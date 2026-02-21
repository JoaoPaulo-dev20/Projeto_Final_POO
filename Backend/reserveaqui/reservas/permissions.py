from rest_framework import permissions


class IsOwnerOrAdminForReservas(permissions.BasePermission):
    """
    Permissão customizada para reservas:
    - Leitura: usuário dono da reserva ou admin
    - Escrita: usuário dono da reserva ou admin
    """
    
    def has_permission(self, request, view):
        """Permite acesso apenas para usuários autenticados"""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica se o usuário pode acessar/editar a reserva específica.
        - Admin pode ver e editar todas as reservas
        - Usuário comum só pode ver e editar suas próprias reservas
        """
        # Verificar se é admin
        is_admin = request.user.usuariopapel_set.filter(
            papel__nome__in=['admin_sistema', 'admin_secundario']
        ).exists()
        
        if is_admin:
            return True
        
        # Usuário comum só pode acessar suas próprias reservas
        return obj.usuario == request.user


class IsAdminOrReadAuthenticated(permissions.BasePermission):
    """
    Permissão para:
    - Leitura: qualquer usuário autenticado
    - Escrita: apenas admins
    """
    
    def has_permission(self, request, view):
        """
        Permite leitura para autenticados e escrita apenas para admins
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Permitir leitura para todos autenticados
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Escrita apenas para admins
        return request.user.usuariopapel_set.filter(
            papel__nome__in=['admin_sistema', 'admin_secundario']
        ).exists()
