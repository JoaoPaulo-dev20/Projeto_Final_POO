from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Mesa
from .serializers import MesaSerializer, MesaListSerializer
from .permissions import IsAdminForWriteOrReadOnly, IsAdminOrProprietarioRestaurante, IsFuncionarioOrHigher
from restaurantes.models import RestauranteUsuario


class MesaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar mesas.
    
    list: Listar todas as mesas
    retrieve: Detalhes de uma mesa específica
    create: Cadastrar nova mesa (apenas admin - RN05)
    update: Atualizar mesa (apenas admin ou proprietário - RN05)
    partial_update: Atualizar parcialmente mesa (apenas admin ou proprietário - RN05)
    destroy: Remover mesa (apenas admin - RN05)
    disponibilidade: Consultar mesas disponíveis por data e horário
    """
    
    queryset = Mesa.objects.select_related('restaurante').all()
    permission_classes = [IsAuthenticated, IsAdminForWriteOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['restaurante', 'status', 'ativa']
    ordering_fields = ['numero', 'restaurante', 'status']
    ordering = ['restaurante', 'numero']
    
    def get_serializer_class(self):
        """Retorna o serializer apropriado para cada ação"""
        if self.action == 'list':
            return MesaListSerializer
        return MesaSerializer
    
    def get_permissions(self):
        """Define permissões específicas por ação"""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrProprietarioRestaurante()]
        return super().get_permissions()
    
    def get_queryset(self):
        """
        Filtra mesas baseado no papel do usuário:
        - admin_sistema: Vê todas as mesas de todos os restaurantes
        - admin_secundario: Vê apenas mesas de seu restaurante
        - funcionario: Vê apenas mesas de seu restaurante (via RestauranteUsuario)
        - cliente: Via query param restaurante_id apenas
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return queryset.none()
        
        # Admin_sistema vê todas
        is_admin_sistema = user.usuariopapel_set.filter(
            papel__nome='admin_sistema'
        ).exists()
        
        if is_admin_sistema:
            # Sem filtro restritivo - vê tudo
            pass
        else:
            # Admin_secundario: vê apenas seu restaurante (como proprietário)
            is_admin_secundario = user.usuariopapel_set.filter(
                papel__nome='admin_secundario'
            ).exists()
            
            if is_admin_secundario:
                # Apenas mesas do restaurante que é proprietário
                from restaurantes.models import Restaurante
                seu_restaurante = Restaurante.objects.filter(proprietario=user).first()
                if seu_restaurante:
                    queryset = queryset.filter(restaurante=seu_restaurante)
                else:
                    return queryset.none()
            else:
                # Funcionário: vê apenas do restaurante onde trabalha
                is_funcionario = user.usuariopapel_set.filter(
                    papel__nome='funcionario'
                ).exists()
                
                if is_funcionario:
                    # Buscar restaurantes onde trabalha
                    restaurantes_ids = RestauranteUsuario.objects.filter(
                        usuario=user,
                        papel__nome='funcionario'
                    ).values_list('restaurante_id', flat=True)
                    
                    if restaurantes_ids:
                        queryset = queryset.filter(restaurante_id__in=restaurantes_ids)
                    else:
                        return queryset.none()
                else:
                    # Cliente: sem acesso direto via list
                    # Vê apenas via query param restaurante_id
                    return queryset.none()
        
        # Filtro por restaurante via query param (override)
        restaurante_id = self.request.query_params.get('restaurante_id', None)
        if restaurante_id:
            queryset = queryset.filter(restaurante_id=restaurante_id)
        
        # Por padrão, mostra apenas mesas ativas
        mostrar_inativas = self.request.query_params.get('mostrar_inativas', 'false')
        if mostrar_inativas.lower() != 'true':
            queryset = queryset.filter(ativa=True)
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='disponibilidade')
    def disponibilidade(self, request):
        """
        Consulta disponibilidade de mesas por data e horário.
        
        Query params:
        - restaurante_id (obrigatório): ID do restaurante
        - data (obrigatório): Data no formato YYYY-MM-DD
        - horario (obrigatório): Horário no formato HH:MM
        - quantidade_pessoas (opcional): Quantidade de pessoas
        
        Retorna mesas disponíveis que não possuem reservas confirmadas
        no horário especificado.
        """
        restaurante_id = request.query_params.get('restaurante_id')
        data_str = request.query_params.get('data')
        horario_str = request.query_params.get('horario')
        quantidade_pessoas = request.query_params.get('quantidade_pessoas')
        
        # Validações
        if not restaurante_id:
            return Response(
                {"error": "O parâmetro 'restaurante_id' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not data_str:
            return Response(
                {"error": "O parâmetro 'data' é obrigatório (formato: YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not horario_str:
            return Response(
                {"error": "O parâmetro 'horario' é obrigatório (formato: HH:MM)."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data_reserva = datetime.strptime(data_str, '%Y-%m-%d').date()
            horario_reserva = datetime.strptime(horario_str, '%H:%M').time()
        except ValueError:
            return Response(
                {"error": "Formato de data ou horário inválido. Use YYYY-MM-DD para data e HH:MM para horário."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar se a data/horário não é no passado
        data_hora_reserva = timezone.make_aware(
            datetime.combine(data_reserva, horario_reserva)
        )
        if data_hora_reserva < timezone.now():
            return Response(
                {"error": "Não é possível consultar disponibilidade para datas/horários no passado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Buscar mesas do restaurante que estão disponíveis
        mesas_disponiveis = Mesa.objects.filter(
            restaurante_id=restaurante_id,
            status='disponivel',
            ativa=True
        )
        
        # Importar Reserva para verificar conflitos
        from reservas.models import Reserva, ReservaMesa
        
        # Buscar reservas confirmadas ou pendentes para essa data/horário
        # Considera um intervalo de 2 horas (1h antes e 1h depois)
        horario_inicio = (datetime.combine(data_reserva, horario_reserva) - timedelta(hours=1)).time()
        horario_fim = (datetime.combine(data_reserva, horario_reserva) + timedelta(hours=1)).time()
        
        reservas_ativas = Reserva.objects.filter(
            restaurante_id=restaurante_id,
            data_reserva=data_reserva,
            horario__gte=horario_inicio,
            horario__lte=horario_fim,
            status__in=['pendente', 'confirmada']
        )
        
        # IDs das mesas ocupadas nessas reservas
        mesas_ocupadas_ids = ReservaMesa.objects.filter(
            reserva__in=reservas_ativas
        ).values_list('mesa_id', flat=True)
        
        # Excluir mesas ocupadas
        mesas_disponiveis = mesas_disponiveis.exclude(id__in=mesas_ocupadas_ids)
        
        # Se quantidade_pessoas foi informada, calcular quantas mesas são necessárias
        info_adicional = {}
        if quantidade_pessoas:
            try:
                qtd_pessoas = int(quantidade_pessoas)
                import math
                mesas_necessarias = math.ceil(qtd_pessoas / 4)
                info_adicional = {
                    "quantidade_pessoas": qtd_pessoas,
                    "mesas_necessarias": mesas_necessarias,
                    "mesas_disponiveis_suficientes": mesas_disponiveis.count() >= mesas_necessarias
                }
            except ValueError:
                pass
        
        serializer = MesaSerializer(mesas_disponiveis, many=True)
        
        return Response({
            "restaurante_id": restaurante_id,
            "data": data_str,
            "horario": horario_str,
            "total_mesas_disponiveis": mesas_disponiveis.count(),
            **info_adicional,
            "mesas": serializer.data
        })
    
    @action(detail=True, methods=['patch'])
    def alternar_status(self, request, pk=None):
        """
        Alterna o status da mesa entre disponível e ocupada.
        Permitido para: admin_sistema, admin_secundario, funcionario
        
        Body: { "status": "disponivel"|"ocupada" }
        """
        mesa = self.get_object()
        novo_status = request.data.get('status')
        
        if novo_status not in ['disponivel', 'ocupada']:
            return Response(
                {"error": "Status inválido. Use: disponivel ou ocupada."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar permissão: admin_sistema, admin_secundario ou funcionario
        user = request.user
        
        # Admin_sistema: tudo bem
        is_admin_sistema = user.usuariopapel_set.filter(
            papel__nome='admin_sistema'
        ).exists()
        
        if not is_admin_sistema:
            # Admin_secundario: deve ser proprietário
            if user == mesa.restaurante.proprietario:
                pass  # OK
            else:
                # Funcionário: deve trabalhar naquele restaurante
                is_funcionario = user.usuariopapel_set.filter(
                    papel__nome='funcionario'
                ).exists()
                
                if is_funcionario:
                    # Validar que trabalha no restaurante
                    trabalha_aqui = RestauranteUsuario.objects.filter(
                        usuario=user,
                        restaurante=mesa.restaurante,
                        papel__nome='funcionario'
                    ).exists()
                    
                    if not trabalha_aqui:
                        return Response(
                            {"error": "Você não trabalha neste restaurante."},
                            status=status.HTTP_403_FORBIDDEN
                        )
                else:
                    # Outro papel sem permissão
                    return Response(
                        {"error": "Apenas administradores e funcionários podem alternar status."},
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        mesa.status = novo_status
        mesa.save()
        
        serializer = self.get_serializer(mesa)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def alternar_ativa(self, request, pk=None):
        """
        Ativa ou desativa uma mesa.
        Apenas admin_sistema pode fazer isso.
        
        Body: { "ativa": true|false }
        """
        # Apenas admin_sistema
        is_admin_sistema = request.user.usuariopapel_set.filter(
            papel__nome='admin_sistema'
        ).exists()
        
        if not is_admin_sistema:
            return Response(
                {"error": "Apenas administradores podem ativar/desativar mesas."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        mesa = self.get_object()
        nova_ativa = request.data.get('ativa')
        
        if not isinstance(nova_ativa, bool):
            return Response(
                {"error": "O campo 'ativa' deve ser booleano (true ou false)."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        mesa.ativa = nova_ativa
        mesa.save()
        
        serializer = self.get_serializer(mesa)
        return Response(serializer.data)
