from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from datetime import timedelta
import secrets
import string


class Papel(models.Model):
    """Define os papéis (roles) disponíveis no sistema"""
    
    TIPOS_PAPEL = [
        ('admin_sistema', 'Admin do Sistema'),
        ('admin_secundario', 'Admin Secundário'),
        ('funcionario', 'Funcionário'),
        ('cliente', 'Cliente'),
    ]
    
    tipo = models.CharField(
        max_length=20, 
        choices=TIPOS_PAPEL, 
        unique=True,
        verbose_name="Tipo de Papel"
    )
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Papel"
        verbose_name_plural = "Papéis"
        ordering = ['tipo']
    
    def __str__(self):
        return self.get_tipo_display()


class Usuario(AbstractUser):
    """Modelo customizado de usuário para o sistema"""
    
    nome = models.CharField(max_length=150, verbose_name="Nome")
    email = models.EmailField(unique=True, verbose_name="Email")
    papeis = models.ManyToManyField(Papel, through='UsuarioPapel', verbose_name="Papéis")
    precisa_trocar_senha = models.BooleanField(
        default=False, 
        verbose_name="Precisa Trocar Senha",
        help_text="Indica se o usuário precisa trocar a senha no próximo login"
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'nome']
    
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.nome} ({self.email})"
    
    def tem_papel(self, tipo_papel):
        """Verifica se usuário tem um papel específico"""
        return self.papeis.filter(tipo=tipo_papel).exists()
    
    @staticmethod
    def gerar_senha_generica():
        """Gera uma senha genérica segura de 12 caracteres"""
        caracteres = string.ascii_letters + string.digits + "!@#$%&*"
        senha = ''.join(secrets.choice(caracteres) for _ in range(12))
        return senha


class UsuarioPapel(models.Model):
    """Modelo intermediário para rastrear papéis de usuários"""
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, verbose_name="Usuário")
    papel = models.ForeignKey(Papel, on_delete=models.CASCADE, verbose_name="Papel")
    data_atribuicao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Atribuição")
    
    class Meta:
        unique_together = ('usuario', 'papel')
        verbose_name = "Usuário-Papel"
        verbose_name_plural = "Usuários-Papéis"
        ordering = ['data_atribuicao']
    
    def __str__(self):
        return f"{self.usuario.nome} - {self.papel.get_tipo_display()}"


class PasswordResetToken(models.Model):
    """
    Modelo para armazenar tokens de recuperação de senha.
    Permite que usuários recuperem suas contas via email validado.
    """
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='password_reset_token',
        verbose_name='Usuário'
    )
    token = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Token'
    )
    email = models.EmailField(verbose_name='Email do Usuário')
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')
    data_expiracao = models.DateTimeField(verbose_name='Data de Expiração')
    utilizado = models.BooleanField(default=False, verbose_name='Token Utilizado')
    
    class Meta:
        verbose_name = 'Token de Recuperação de Senha'
        verbose_name_plural = 'Tokens de Recuperação de Senha'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Reset Token - {self.usuario.email}"
    
    def esta_valido(self):
        """Verifica se o token ainda é válido (não expirou e não foi utilizado)"""
        return not self.utilizado and timezone.now() < self.data_expiracao
    
    @staticmethod
    def gerar_token_recuperacao(usuario):
        """
        Gera um novo token de recuperação para o usuário.
        Token expira em 24 horas.
        """
        # Gerar token seguro
        token = default_token_generator.make_token(usuario)
        
        # Remover token antigo se existir
        PasswordResetToken.objects.filter(usuario=usuario).delete()
        
        # Criar novo token
        data_expiracao = timezone.now() + timedelta(hours=24)
        
        reset_token = PasswordResetToken.objects.create(
            usuario=usuario,
            token=token,
            email=usuario.email,
            data_expiracao=data_expiracao
        )
        
        return reset_token
