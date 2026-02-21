from rest_framework import permissions


class IsAdminSystemOnly(permissions.BasePermission):
    """
    Permissão que permite apenas admin_sistema.
    Usado para operações críticas como deletar restaurante.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Apenas admin_sistema (não admin_secundario)
        return request.user.usuariopapel_set.filter(
            papel__nome='admin_sistema'
        ).exists()


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permissão customizada que permite:
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
        
        # Verifica se o usuário tem papel de admin
        return request.user.usuariopapel_set.filter(
            papel__nome__in=['admin_sistema', 'admin_secundario']
        ).exists()


class IsProprietarioOrAdmin(permissions.BasePermission):
    """
    Permissão que permite:
    - Proprietário do restaurante pode editar
    - Administradores podem editar qualquer restaurante
    """
    
    def has_object_permission(self, request, view, obj):
        # Permite leitura para qualquer usuário autenticado
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Para escrita, verifica se é proprietário ou admin
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Proprietário do restaurante
        if obj.proprietario == request.user:
            return True
        
        # Administrador do sistema
        return request.user.usuariopapel_set.filter(
            papel__nome__in=['admin_sistema', 'admin_secundario']
        ).exists()
