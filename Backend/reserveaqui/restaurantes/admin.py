from django.contrib import admin
from .models import Restaurante, RestauranteUsuario


class RestauranteUsuarioInline(admin.TabularInline):
    model = RestauranteUsuario
    extra = 1


@admin.register(Restaurante)
class RestauranteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cidade', 'proprietario', 'ativo', 'data_criacao')
    list_filter = ('ativo', 'cidade', 'data_criacao')
    search_fields = ('nome', 'cidade', 'email')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    inlines = [RestauranteUsuarioInline]
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao', 'proprietario', 'ativo')
        }),
        ('Localização', {
            'fields': ('endereco', 'cidade', 'estado', 'cep')
        }),
        ('Contato', {
            'fields': ('email', 'telefone')
        }),
        ('Datas', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RestauranteUsuario)
class RestauranteUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'restaurante', 'papel', 'data_vinculacao')
    list_filter = ('papel', 'restaurante', 'data_vinculacao')
    search_fields = ('usuario__nome', 'restaurante__nome')
    readonly_fields = ('data_vinculacao',)
