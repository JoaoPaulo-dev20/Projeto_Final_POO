from rest_framework import permissions
from restaurantes.models import RestauranteUsuario


class IsFuncionarioOrHigher(permissions.BasePermission):
    """
    Permissão para ações que funcionário pode fazer em mesas.
    Valida que funcionário trabalha no restaurante.
    """
    
    def has_object_permission(self, request, view, obj):
        """Valida que funcionário trabalha no restaurante da mesa"""
        user = request.user
        
        # Admin_sistema pode fazer tudo
        if user.usuariopapel_set.filter(papel__nome='admin_sistema').exists():
            return True
        
        # Admin_secundario se for proprietário do restaurante
        if obj.restaurante.proprietario == user:
            return True
        
        # Funcionário: validar que trabalha naquele restaurante
        if user.usuariopapel_set.filter(papel__nome='funcionario').exists():
            return RestauranteUsuario.objects.filter(
                usuario=user,
                restaurante=obj.restaurante,
                papel__nome='funcionario'
            ).exists()
        
        return False


class IsAdminForWriteOrReadOnly(permissions.BasePermission):
    """
    Permissão customizada para mesas (RN05):
    - Leitura para qualquer usuário autenticado
    - Escrita apenas para administradores (admin_sistema ou admin_secundario)
    """
    
    def has_permission(self, request, view):
        # Permite métodos de leitura (GET, HEAD, OPTIONS) para usuários autenticados
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Para métodos de escrita, verifica se é admin
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Verifica se o usuário tem papel de admin (RN05)
        return request.user.usuariopapel_set.filter(
            papel__nome__in=['admin_sistema', 'admin_secundario']
        ).exists()


class IsAdminOrProprietarioRestaurante(permissions.BasePermission):
    """
    Permissão que permite:
    - Proprietário do restaurante pode gerenciar suas mesas
    - Administradores podem gerenciar qualquer mesa
    """
    
    def has_object_permission(self, request, view, obj):
        # Permite leitura para qualquer usuário autenticado
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Para escrita, verifica se é proprietário do restaurante ou admin
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Proprietário do restaurante da mesa
        if obj.restaurante.proprietario == request.user:
            return True
        
        # Administrador do sistema
        return request.user.usuariopapel_set.filter(
            papel__nome__in=['admin_sistema', 'admin_secundario']
        ).exists()
