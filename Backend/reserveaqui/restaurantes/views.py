from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Restaurante, RestauranteUsuario
from .serializers import (
    RestauranteSerializer,
    RestauranteListSerializer,
    RestauranteCreateUpdateSerializer,
    RestauranteUsuarioSerializer,
    AdicionarFuncionarioSerializer
)
from .permissions import IsAdminOrReadOnly, IsProprietarioOrAdmin, IsAdminSystemOnly
from usuarios.models import Usuario, Papel
from usuarios.utils import enviar_senha_generica


class RestauranteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar restaurantes.
    
    list: Listar todos os restaurantes ativos
    retrieve: Detalhes de um restaurante específico
    create: Cadastrar novo restaurante (apenas admin)
    update: Atualizar restaurante (proprietário ou admin)
    partial_update: Atualizar parcialmente restaurante (proprietário ou admin)
    destroy: Remover restaurante (apenas admin)
    """
    
    queryset = Restaurante.objects.select_related('proprietario').prefetch_related('mesas').all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['cidade', 'estado', 'ativo']
    search_fields = ['nome', 'cidade', 'endereco']
    ordering_fields = ['nome', 'cidade', 'data_criacao']
    ordering = ['nome']
    
    def get_serializer_class(self):
        """Retorna o serializer apropriado para cada ação"""
        if self.action == 'list':
            return RestauranteListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return RestauranteCreateUpdateSerializer
        return RestauranteSerializer
    
    def get_permissions(self):
        """Define permissões específicas por ação"""
        if self.action in ['update', 'partial_update']:
            return [IsAuthenticated(), IsProprietarioOrAdmin()]
        elif self.action == 'destroy':
            # Apenas admin_sistema pode deletar restaurante (não admin_secundario)
            return [IsAuthenticated(), IsAdminSystemOnly()]
        return super().get_permissions()
    
    def get_queryset(self):
        """
        Filtra restaurantes baseado no papel do usuário:
        - admin_sistema: Vê todos (incluindo inativos)
        - admin_secundario: Vê apenas seu restaurante (como proprietário)
        - Outros autenticados: Veem apenas restaurantes ativos
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return queryset.filter(ativo=True)
        
        # Admin_sistema vê todos (incluindo inativos)
        is_admin_sistema = user.usuariopapel_set.filter(
            papel__nome='admin_sistema'
        ).exists()
        
        if is_admin_sistema:
            return queryset  # Vê tudo
        
        # Admin_secundario vê apenas seu restaurante
        is_admin_secundario = user.usuariopapel_set.filter(
            papel__nome='admin_secundario'
        ).exists()
        
        if is_admin_secundario:
            # Admin_secundario é proprietário de apenas 1 restaurante
            restaurante = queryset.filter(proprietario=user).first()
            if restaurante:
                return queryset.filter(id=restaurante.id)
            else:
                return queryset.none()
        
        # Clientes e funcionários veem apenas restaurantes ativos
        return queryset.filter(ativo=True)
    
    def perform_create(self, serializer):
        """Ao criar restaurante, cria também o proprietário (admin_secundario) com senha genérica"""
        proprietario_email = serializer.validated_data.pop('proprietario_email', None)
        proprietario_nome = serializer.validated_data.pop('proprietario_nome', None)
        
        # Gerar senha genérica
        senha_generica = Usuario.gerar_senha_generica()
        
        # Criar usuário admin_secundario
        username = proprietario_email.split('@')[0]
        proprietario = Usuario.objects.create_user(
            username=username,
            email=proprietario_email,
            nome=proprietario_nome,
            password=senha_generica
        )
        
        # Marcar para trocar senha no primeiro acesso
        proprietario.precisa_trocar_senha = True
        proprietario.save()
        
        # Adicionar papel admin_secundario
        papel_admin = Papel.objects.get(tipo='admin_secundario')
        proprietario.papeis.add(papel_admin)
        
        # Enviar senha por email
        enviar_senha_generica(proprietario, senha_generica, 'Administrador Secundário')
        
        # Salvar restaurante com proprietário
        restaurante = serializer.save(proprietario=proprietario)
        
        # Vincular proprietário ao restaurante na tabela RestauranteUsuario
        RestauranteUsuario.objects.create(
            restaurante=restaurante,
            usuario=proprietario,
            papel='admin_secundario'
        )
    
    @action(detail=True, methods=['get'])
    def mesas(self, request, pk=None):
        """Retorna as mesas do restaurante"""
        restaurante = self.get_object()
        mesas = restaurante.mesas.all()
        
        # Importar serializer de mesas (será criado depois)
        from mesas.serializers import MesaSerializer
        serializer = MesaSerializer(mesas, many=True)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def equipe(self, request, pk=None):
        """Retorna a equipe vinculada ao restaurante"""
        restaurante = self.get_object()
        vinculos = RestauranteUsuario.objects.filter(restaurante=restaurante)
        serializer = RestauranteUsuarioSerializer(vinculos, many=True)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def adicionar_usuario(self, request, pk=None):
        """Adiciona um usuário à equipe do restaurante"""
        restaurante = self.get_object()
        
        # Verifica se é proprietário ou admin
        if restaurante.proprietario != request.user:
            is_admin = request.user.usuariopapel_set.filter(
                papel__nome__in=['admin_sistema', 'admin_secundario']
            ).exists()
            if not is_admin:
                return Response(
                    {"detail": "Apenas o proprietário ou administradores podem adicionar usuários."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        data = request.data.copy()
        data['restaurante'] = restaurante.id
        
        serializer = RestauranteUsuarioSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def adicionar_funcionario(self, request, pk=None):
        """
        Endpoint para admin_secundario criar funcionários do seu restaurante.
        Cria o usuário com senha genérica enviada por email.
        """
        restaurante = self.get_object()
        
        # Verifica se é o proprietário (admin_secundario) do restaurante
        if restaurante.proprietario != request.user:
            return Response(
                {"detail": "Apenas o proprietário do restaurante pode adicionar funcionários."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = AdicionarFuncionarioSerializer(data=request.data)
        if serializer.is_valid():
            # Gerar senha genérica
            senha_generica = Usuario.gerar_senha_generica()
            
            # Criar usuário funcionário
            email = serializer.validated_data['email']
            nome = serializer.validated_data['nome']
            
            username = email.split('@')[0]
            funcionario = Usuario.objects.create_user(
                username=username,
                email=email,
                nome=nome,
                password=senha_generica
            )
            
            # Marcar para trocar senha no primeiro acesso
            funcionario.precisa_trocar_senha = True
            funcionario.save()
            
            # Adicionar papel de funcionário
            papel_funcionario = Papel.objects.get(tipo='funcionario')
            funcionario.papeis.add(papel_funcionario)
            
            # Vincular ao restaurante
            RestauranteUsuario.objects.create(
                restaurante=restaurante,
                usuario=funcionario,
                papel='funcionario'
            )
            
            # Enviar senha por email
            enviar_senha_generica(funcionario, senha_generica, 'Funcionário')
            
            return Response({
                'mensagem': 'Funcionário adicionado com sucesso! Uma senha temporária foi enviada para o email.',
                'funcionario': {
                    'id': funcionario.id,
                    'email': funcionario.email,
                    'nome': funcionario.nome
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RestauranteUsuarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar vínculos de usuários a restaurantes.
    """
    
    queryset = RestauranteUsuario.objects.select_related('restaurante', 'usuario').all()
    serializer_class = RestauranteUsuarioSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['restaurante', 'usuario', 'papel']
    
    def get_queryset(self):
        """Filtra vínculos baseado no usuário"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Admin vê tudo
        is_admin = user.usuariopapel_set.filter(
            papel__nome__in=['admin_sistema', 'admin_secundario']
        ).exists()
        
        if is_admin:
            return queryset
        
        # Proprietários veem seus restaurantes
        restaurantes_proprietario = Restaurante.objects.filter(proprietario=user)
        return queryset.filter(restaurante__in=restaurantes_proprietario)
