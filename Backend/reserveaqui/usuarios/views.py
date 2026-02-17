from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Usuario
from .serializers import UsuarioSerializer, LoginSerializer, TrocarSenhaSerializer


class UsuarioViewSet(viewsets.ModelViewSet):
    """ViewSet para cadastro e gerenciamento de usuários"""
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def cadastro(self, request):
        """Endpoint para cadastro de novo usuário"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'mensagem': 'Usuário cadastrado com sucesso!', 'usuario': serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Endpoint para retornar dados do usuário autenticado"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """Endpoint para login e geração de tokens JWT"""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            usuario = serializer.validated_data['usuario']
            refresh = RefreshToken.for_user(usuario)
            
            return Response({
                'mensagem': 'Login realizado com sucesso!',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'usuario': {
                    'id': usuario.id,
                    'email': usuario.email,
                    'nome': usuario.nome,
                    'papeis': [{'tipo': p.tipo, 'descricao': p.get_tipo_display()} for p in usuario.papeis.all()],
                }
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def trocar_senha(self, request):
        """Endpoint para trocar senha do usuário autenticado"""
        serializer = TrocarSenhaSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            usuario = request.user
            nova_senha = serializer.validated_data['nova_senha']
            usuario.set_password(nova_senha)
            usuario.save()
            
            return Response({
                'mensagem': 'Senha alterada com sucesso!'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
