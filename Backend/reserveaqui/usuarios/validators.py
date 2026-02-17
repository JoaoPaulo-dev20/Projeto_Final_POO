from django.core.exceptions import ValidationError
import re


def validar_forca_senha(senha):
    """
    Valida a força da senha:
    - Mínimo 8 caracteres
    - Pelo menos 1 letra maiúscula
    - Pelo menos 1 número
    """
    if len(senha) < 8:
        raise ValidationError('Senha deve ter no mínimo 8 caracteres.')
    
    if not re.search(r'[A-Z]', senha):
        raise ValidationError('Senha deve conter pelo menos 1 letra maiúscula.')
    
    if not re.search(r'[0-9]', senha):
        raise ValidationError('Senha deve conter pelo menos 1 número.')
