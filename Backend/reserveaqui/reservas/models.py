from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import math
from usuarios.models import Usuario
from restaurantes.models import Restaurante
from mesas.models import Mesa


class Reserva(models.Model):
    """
    Modelo para gerenciar reservas de mesas em restaurantes.
    Uma reserva pode ocupar múltiplas mesas dependendo da quantidade de pessoas.
    """
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('concluida', 'Concluída'),
    ]
    
    # Relações
    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name='Restaurante'
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas',
        verbose_name='Usuário',
        help_text='Usuário cadastrado que fez a reserva (opcional)'
    )
    mesas = models.ManyToManyField(
        Mesa,
        through='ReservaMesa',
        related_name='reservas',
        verbose_name='Mesas'
    )
    
    # Dados da reserva
    data_reserva = models.DateField(verbose_name='Data da Reserva')
    horario = models.TimeField(verbose_name='Horário')
    quantidade_pessoas = models.PositiveIntegerField(verbose_name='Quantidade de Pessoas')
    
    # Dados do cliente
    nome_cliente = models.CharField(max_length=200, verbose_name='Nome do Cliente')
    telefone_cliente = models.CharField(max_length=20, verbose_name='Telefone do Cliente')
    email_cliente = models.EmailField(blank=True, verbose_name='Email do Cliente')
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    
    # Status e controle
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name='Status'
    )
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')
    
    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-data_reserva', '-horario']
        indexes = [
            models.Index(fields=['restaurante', 'data_reserva', 'horario']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.nome_cliente} - {self.restaurante.nome} ({self.data_reserva} às {self.horario})"
    
    def calcular_mesas_necessarias(self):
        """Calcula quantas mesas de 4 pessoas são necessárias para a reserva"""
        return math.ceil(self.quantidade_pessoas / 4)
    
    def pode_cancelar(self):
        """Verifica se a reserva ainda pode ser cancelada"""
        if self.status in ['cancelada', 'concluida']:
            return False
        
        # Permite cancelar até 2 horas antes da reserva
        data_hora_reserva = timezone.make_aware(
            timezone.datetime.combine(self.data_reserva, self.horario)
        )
        limite_cancelamento = data_hora_reserva - timedelta(hours=2)
        
        return timezone.now() < limite_cancelamento
    
    def clean(self):
        """Validações do modelo"""
        super().clean()
        
        # RN01: Reserva deve ser feita com no mínimo 2 horas de antecedência
        if self.data_reserva and self.horario:
            data_hora_reserva = timezone.make_aware(
                timezone.datetime.combine(self.data_reserva, self.horario)
            )
            limite_minimo = timezone.now() + timedelta(hours=2)
            
            if data_hora_reserva < limite_minimo:
                raise ValidationError(
                    'Reservas devem ser feitas com no mínimo 2 horas de antecedência.'
                )
        
        # Validar que quantidade de pessoas é razoável
        if self.quantidade_pessoas is not None and self.quantidade_pessoas < 1:
            raise ValidationError('A quantidade de pessoas deve ser maior que zero.')
    
    def save(self, *args, **kwargs):
        """Sobrescreve o save para executar validações"""
        skip_validation = kwargs.pop('skip_validation', False)
        if not skip_validation:
            self.full_clean()
        super().save(*args, **kwargs)


class ReservaMesa(models.Model):
    """
    Modelo intermediário para relacionamento entre Reserva e Mesa.
    Permite rastrear quais mesas estão alocadas para cada reserva.
    """
    
    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        verbose_name='Reserva'
    )
    mesa = models.ForeignKey(
        Mesa,
        on_delete=models.CASCADE,
        verbose_name='Mesa'
    )
    data_vinculacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Vinculação'
    )
    
    class Meta:
        verbose_name = 'Reserva-Mesa'
        verbose_name_plural = 'Reservas-Mesas'
        unique_together = ['reserva', 'mesa']
    
    def __str__(self):
        return f"Reserva {self.reserva.id} - Mesa {self.mesa.numero}"

class Notificacao(models.Model):
    """
    Modelo para armazenar notificações de reservas.
    RF07: Informar ao cliente a confirmação da reserva.
    """
    
    TIPO_NOTIFICACAO = [
        ('confirmacao', 'Confirmação de Reserva'),
        ('cancelamento', 'Cancelamento de Reserva'),
        ('lembranca', 'Lembrança de Reserva'),
        ('atualizacao', 'Atualização de Reserva'),
    ]
    
    # Relações
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='notificacoes',
        verbose_name='Usuário'
    )
    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='notificacoes',
        verbose_name='Reserva'
    )
    
    # Dados da notificação
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_NOTIFICACAO,
        default='confirmacao',
        verbose_name='Tipo de Notificação'
    )
    titulo = models.CharField(max_length=200, verbose_name='Título')
    mensagem = models.TextField(verbose_name='Mensagem')
    lido = models.BooleanField(default=False, verbose_name='Lido')
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')
    data_leitura = models.DateTimeField(null=True, blank=True, verbose_name='Data de Leitura')
    
    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['usuario', 'lido']),
            models.Index(fields=['usuario', '-data_criacao']),
        ]
    
    def __str__(self):
        return f"{self.titulo} - {self.usuario.email}"
    
    def marcar_como_lida(self):
        """Marca a notificação como lida"""
        self.lido = True
        self.data_leitura = timezone.now()
        self.save()