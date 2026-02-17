# Backend - Sistema de Gerenciamento de Mesas

Backend desenvolvido em **Django 6.0.2** com **Django REST Framework** e **JWT Authentication**.

## Requisitos

- Python 3.10+
- Django 6.0.2
- djangorestframework 3.14.0
- djangorestframework-simplejwt 5.5.0

## Setup Inicial

```powershell
cd Backend/reserveaqui
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse: `http://127.0.0.1:8000/`

---

## App: Usuarios

### Modelos:
- **Usuario**: Usuário customizado (email como identificador)
- **Papel**: Define os 4 papéis (admin_sistema, admin_secundario, funcionario, cliente)
- **UsuarioPapel**: Relacionamento entre Usuários e Papéis

### Endpoints:

| `/api/usuarios/cadastro/` | POST | Cadastrar novo usuário 
| `/api/usuarios/login/` | POST | Login e obter tokens 
| `/api/usuarios/me/` | GET | Dados do usuário logado 
| `/api/usuarios/trocar_senha/` | POST | Trocar senha 
| `/api/token/refresh/` | POST | Renovar token 

### Validações de Senha:
- Mínimo 8 caracteres
- Pelo menos 1 letra maiúscula
- Pelo menos 1 número

---

## Admin Panel

`http://127.0.0.1:8000/admin/`