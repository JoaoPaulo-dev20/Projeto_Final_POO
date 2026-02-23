from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from .models import Usuario, PasswordResetToken
from .serializers import (
    UsuarioSerializer, LoginSerializer, TrocarSenhaSerializer,
    SolicitarRecuperacaoSenhaSerializer, RedefinirSenhaSerializer,
    CadastroPublicoSerializer
)


class UsuarioViewSet(viewsets.ModelViewSet):
    """ViewSet para cadastro e gerenciamento de usuários"""
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def cadastro(self, request):
        """Endpoint para cadastro público - cria apenas usuários do tipo cliente"""
        serializer = CadastroPublicoSerializer(data=request.data)
        if serializer.is_valid():
            usuario = serializer.save()
            return Response(
                {'mensagem': 'Usuário cadastrado com sucesso!', 'usuario': UsuarioSerializer(usuario).data},
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
                    'precisa_trocar_senha': usuario.precisa_trocar_senha
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
            
            # Remover flag de precisa trocar senha
            if usuario.precisa_trocar_senha:
                usuario.precisa_trocar_senha = False
            
            usuario.save()
            
            return Response({
                'mensagem': 'Senha alterada com sucesso!'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def solicitar_recuperacao(self, request):
        """
        Endpoint para solicitar recuperação de senha.
        Gera um token e envia por email.
        """
        serializer = SolicitarRecuperacaoSenhaSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                usuario = Usuario.objects.get(email=email)
            except Usuario.DoesNotExist:
                # Não revelar se o email existe ou não (por segurança)
                return Response({
                    'mensagem': 'Se o email está cadastrado, um link de recuperação será enviado.'
                }, status=status.HTTP_200_OK)
            
            # Gerar token de recuperação
            reset_token = PasswordResetToken.gerar_token_recuperacao(usuario)
            
            # Construir link de recuperação (simulado)
            # Em produção, seria: https://frontend.com/recuperar-senha?token={token}&email={email}
            reset_link = f"{settings.FRONTEND_URL}/recuperar-senha?token={reset_token.token}&email={email}" if hasattr(settings, 'FRONTEND_URL') else f"Token: {reset_token.token}"
            
            # Tentar enviar email
            try:
                send_mail(
                    assunto='Recuperação de Senha - ReserveAqui',
                    mensagem=f"""
Olá {usuario.nome},

Você solicitou recuperação de senha. Clique no link abaixo para redefinir sua senha:

{reset_link}

Este link expira em 24 horas.

Se você não solicitou esta recuperação, ignore este email.

Atenciosamente,
Equipe ReserveAqui
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[usuario.email],
                    fail_silently=False,
                )
                email_enviado = True
            except Exception as e:
                # Em desenvolvimento, apenas registrar que o email não foi enviado
                print(f"Erro ao enviar email: {e}")
                email_enviado = False
            
            return Response({
                'mensagem': 'Se o email está cadastrado, um link de recuperação será enviado.',
                'debug_token': reset_token.token if not email_enviado else None,  # Apenas para testes
                'email_enviado': email_enviado
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def redefinir_senha(self, request):
        """
        Endpoint para redefinir senha usando token de recuperação.
        Valida o token antes de permitir a redefinição.
        """
        serializer = RedefinirSenhaSerializer(data=request.data)
        if serializer.is_valid():
            reset_token = serializer.validated_data['reset_token']
            nova_senha = serializer.validated_data['nova_senha']
            
            usuario = reset_token.usuario
            usuario.set_password(nova_senha)
            usuario.save()
            
            # Marcar token como utilizado
            reset_token.utilizado = True
            reset_token.save()
            
            return Response({
                'mensagem': 'Senha redefinida com sucesso! Você já pode fazer login com a nova senha.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)