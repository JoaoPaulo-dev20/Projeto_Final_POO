from django.contrib import admin
from .models import Reserva, ReservaMesa, Notificacao


class ReservaMesaInline(admin.TabularInline):
    """Inline para exibir mesas vinculadas à reserva"""
    model = ReservaMesa
    extra = 1
    readonly_fields = ['data_vinculacao']


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    """Admin para o modelo Reserva"""
    
    list_display = [
        'id',
        'nome_cliente',
        'restaurante',
        'data_reserva',
        'horario',
        'quantidade_pessoas',
        'status',
        'data_criacao'
    ]
    
    list_filter = [
        'status',
        'data_reserva',
        'restaurante',
        'data_criacao'
    ]
    
    search_fields = [
        'nome_cliente',
        'telefone_cliente',
        'email_cliente',
        'restaurante__nome'
    ]
    
    readonly_fields = [
        'data_criacao',
        'data_atualizacao',
        'calcular_mesas_necessarias'
    ]
    
    fieldsets = (
        ('Informações da Reserva', {
            'fields': (
                'restaurante',
                'data_reserva',
                'horario',
                'quantidade_pessoas',
                'calcular_mesas_necessarias',
                'status'
            )
        }),
        ('Informações do Cliente', {
            'fields': (
                'usuario',
                'nome_cliente',
                'telefone_cliente',
                'email_cliente',
                'observacoes'
            )
        }),
        ('Controle', {
            'fields': (
                'data_criacao',
                'data_atualizacao'
            )
        })
    )
    
    inlines = [ReservaMesaInline]
    
    def calcular_mesas_necessarias(self, obj):
        """Exibe a quantidade de mesas necessárias"""
        if obj.quantidade_pessoas:
            return f"{obj.calcular_mesas_necessarias()} mesa(s)"
        return "-"
    calcular_mesas_necessarias.short_description = "Mesas Necessárias"


@admin.register(ReservaMesa)
class ReservaMesaAdmin(admin.ModelAdmin):
    """Admin para o modelo ReservaMesa"""
    
    list_display = [
        'id',
        'reserva',
        'mesa',
        'data_vinculacao'
    ]
    
    list_filter = [
        'data_vinculacao',
        'mesa__restaurante'
    ]
    
    search_fields = [
        'reserva__nome_cliente',
        'mesa__numero'
    ]
    
    readonly_fields = ['data_vinculacao']

@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    """Admin para o modelo Notificacao"""
    
    list_display = [
        'id',
        'usuario',
        'titulo',
        'tipo',
        'lido',
        'data_criacao'
    ]
    
    list_filter = [
        'tipo',
        'lido',
        'data_criacao'
    ]
    
    search_fields = [
        'usuario__email',
        'titulo',
        'mensagem'
    ]
    
    readonly_fields = [
        'data_criacao',
        'data_leitura'
    ]
    
    fieldsets = (
        ('Notificação', {
            'fields': (
                'usuario',
                'reserva',
                'tipo',
                'titulo',
                'mensagem'
            )
        }),
        ('Status', {
            'fields': (
                'lido',
                'data_criacao',
                'data_leitura'
            )
        })
    )
    
    actions = ['marcar_como_lidas']
    
    def marcar_como_lidas(self, request, queryset):
        """Action para marcar notificações como lidas"""
        count = queryset.count()
        for notificacao in queryset:
            notificacao.marcar_como_lida()
        self.message_user(request, f'{count} notificação(ões) marcada(s) como lida(s).')
    marcar_como_lidas.short_description = "Marcar selecionadas como lidas"