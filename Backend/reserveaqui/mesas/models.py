from django.db import models
from restaurantes.models import Restaurante


class Mesa(models.Model):
    """Modelo que representa uma mesa em um restaurante
    
    Todas as mesas têm capacidade fixa de 4 pessoas.
    Para reservas maiores, múltiplas mesas são combinadas.
    """
    
    STATUS_CHOICES = [
        ('disponivel', 'Disponível'),
        ('ocupada', 'Ocupada'),
    ]
    
    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name='mesas',
        verbose_name="Restaurante"
    )
    
    numero = models.PositiveIntegerField(verbose_name="Número da Mesa")
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='disponivel',
        verbose_name="Status"
    )
    
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    class Meta:
        verbose_name = "Mesa"
        verbose_name_plural = "Mesas"
        unique_together = ('restaurante', 'numero')
        ordering = ['numero']
    
    def __str__(self):
        return f"Mesa {self.numero} - {self.restaurante.nome} ({self.get_status_display()})"
    
    @property
    def capacidade(self):
        """Capacidade fixa de 4 pessoas por mesa"""
        return 4
    
    def pode_reservar(self):
        """Verifica se mesa pode ser reservada"""
        return self.status == 'disponivel' and self.ativa
