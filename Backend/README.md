# Backend - ReserveAqui API

API REST para gerenciamento de reservas de mesas em restaurantes, desenvolvida em **Django 6.0.2** com **Django REST Framework** e **JWT Authentication**.

## Requisitos

- Python 3.13+
- Django 6.0.2
- djangorestframework 3.14.0
- djangorestframework-simplejwt 5.5.0
- django-filter 24.3
- python-decouple 3.8
- django-cors-headers 4.3.1
- drf-spectacular 0.27.0

## Setup Inicial

### 1. Ambiente Virtual

```powershell
# Navegue até o diretório do backend
cd Backend/reserveaqui

# Crie o ambiente virtual
python -m venv venv

# Ative (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

### 2. Instalar Dependências

```powershell
pip install -r ../requirements.txt
```

### 3. Migrações e Superusuário

```powershell
python manage.py migrate
python manage.py createsuperuser
```

### 4. Executar Servidor

```powershell
python manage.py runserver
```

Acesse: `http://127.0.0.1:8000/`

---

## Autenticação JWT

Todos os endpoints protegidos requerem um token JWT no header:

```
Authorization: Bearer <seu_access_token>
```

### Fluxo:

1. **Login**: `POST /api/usuarios/login/`
   - Retorna: `access` (1h) e `refresh` (7d) tokens

2. **Usar Access Token**: Incluir em todas as requisições
   ```
   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
   ```

3. **Renovar Token**: `POST /api/token/refresh/`
   - Envia `refresh` token, recebe novo `access` token

---

## Endpoints Principais

### **Usuarios** - Autenticação e Gestão de Usuários

| Endpoint | Método | Descrição | Auth |
|----------|--------|-----------|------|
| `/api/usuarios/cadastro/` | POST | Registrar novo usuário | ❌ |
| `/api/usuarios/login/` | POST | Login com JWT | ❌ |
| `/api/usuarios/me/` | GET | Dados do usuário logado | ✅ |
| `/api/usuarios/trocar_senha/` | POST | Mudar senha | ✅ |
| `/api/usuarios/solicitar_recuperacao/` | POST | Recuperar senha (envia email) | ❌ |
| `/api/usuarios/redefinir_senha/` | POST | Redefinir com token | ❌ |

**Validação de Senha**: Mínimo 8 caracteres, 1 letra maiúscula, 1 número

---

### **Restaurantes** - CRUD de Restaurantes

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `/api/restaurantes/` | GET | Listar restaurantes | Autenticado |
| `/api/restaurantes/` | POST | Criar restaurante | Admin |
| `/api/restaurantes/{id}/` | GET | Detalhes | Autenticado |
| `/api/restaurantes/{id}/` | PUT/PATCH | Editar | Proprietário/Admin |
| `/api/restaurantes/{id}/` | DELETE | Deletar | Admin |
| `/api/restaurantes/{id}/mesas/` | GET | Mesas do restaurante | Autenticado |
| `/api/restaurantes/{id}/equipe/` | GET | Equipe | Autenticado |
| `/api/restaurantes/{id}/adicionar_usuario/` | POST | Adicionar usuário | Proprietário/Admin |

**Filtros**: `?search=<nome>`, `?ativo=true/false`, `?ordering=nome`

---

### **Mesas** - Gestão de Mesas

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `/api/mesas/` | GET | Listar mesas | Autenticado |
| `/api/mesas/` | POST | Criar mesa | Admin |
| `/api/mesas/{id}/` | GET | Detalhes | Autenticado |
| `/api/mesas/{id}/` | PUT/PATCH | Editar | Admin |
| `/api/mesas/{id}/` | DELETE | Deletar | Admin |
| `/api/mesas/disponibilidade/` | GET | Verificar disponibilidade | Autenticado |
| `/api/mesas/{id}/alternar_status/` | POST | Mudar status | Funcionário/Admin |
| `/api/mesas/{id}/alternar_ativa/` | POST | Ativar/Desativar | Admin |

**Disponibilidade**: Query params `?data=YYYY-MM-DD`, `?horario=HH:MM`, `?pessoas=N`

---

### **Reservas** - Reservas de Mesas

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `/api/reservas/` | GET | Listar reservas | Admin |
| `/api/reservas/` | POST | Criar reserva | Autenticado |
| `/api/reservas/{id}/` | GET | Detalhes | Dono/Admin |
| `/api/reservas/{id}/` | PUT/PATCH | Editar | Dono/Admin |
| `/api/reservas/{id}/` | DELETE | Cancelar | Dono/Admin |
| `/api/reservas/{id}/confirmar/` | POST | Confirmar reserva | Admin |
| `/api/reservas/{id}/cancelar/` | POST | Cancelar reserva | Dono/Admin |
| `/api/reservas/minhas_reservas/` | GET | Minhas reservas | Autenticado |
| `/api/reservas/ocupacao/` | GET | Relatório de ocupação | Admin |
| `/api/reservas/horarios_movimentados/` | GET | Horários mais movimentados | Admin |
| `/api/reservas/estatisticas_periodo/` | GET | Estatísticas por período | Admin |

**Regras de Negócio**:
- Mínimo 2 horas de antecedência
- Mesas alocadas automaticamente (ceil(pessoas/4))
- Validação de conflitos (±1h)
- Capacidade respeitada por mesa

---

### **Notificações** - Sistema de Notificações

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `/api/notificacoes/` | GET | Listar notificações | Autenticado |
| `/api/notificacoes/{id}/` | GET | Detalhes | Dono |
| `/api/notificacoes/{id}/marcar_como_lida/` | POST | Marcar como lida | Dono |
| `/api/notificacoes/marcar_todas_como_lidas/` | POST | Marcar todas como lidas | Autenticado |
| `/api/notificacoes/nao_lidas/` | GET | Contar não lidas | Autenticado |

**Tipos de Notificações**: confirmacao, cancelamento, lembranca, atualizacao

---

### **Relatórios** - Dados e Análises

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `/api/reservas/ocupacao/` | GET | Taxa de ocupação por data | Admin |
| `/api/reservas/horarios_movimentados/` | GET | 10 horários mais reservados | Admin |
| `/api/reservas/estatisticas_periodo/` | GET | Estatísticas (dia/semana/mês) | Admin |

**Query Params**:
- `?data_inicio=YYYY-MM-DD`
- `?data_fim=YYYY-MM-DD`
- `?restaurante_id=<id>`
- `?tipo_periodo=day/week/month` (para estatísticas)

---

## CORS - Frontend Integration

API configurada para aceitar requisições do frontend React em `localhost:3000`:

```javascript
// Frontend (React/TypeScript)
const response = await fetch('http://localhost:8000/api/usuarios/login/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  credentials: 'include', // Para enviar cookies (se necessário)
  body: JSON.stringify({
    email: 'usuario@example.com',
    password: 'SenhaForte123'
  })
});
```

**Domínios Permitidos**: `localhost:3000`, `localhost:8000`

---

## Documentação Interativa (Swagger)

### Acessar Documentação

#### **Swagger UI** (Recomendado)
- URL: `http://127.0.0.1:8000/api/docs/swagger/`
- Teste endpoints diretamente na interface
- Suporte para autenticação JWT

#### **ReDoc**
- URL: `http://127.0.0.1:8000/api/docs/redoc/`
- Documentação em formato de referência

#### **OpenAPI Schema**
- URL: `http://127.0.0.1:8000/api/schema/`
- Especificação OpenAPI 3.0 em JSON

### Como Usar Swagger

1. Acesse `http://127.0.0.1:8000/api/docs/swagger/`
2. Clique em **"Authorize"**
3. Cole seu JWT token: `Bearer <seu_access_token>`
4. Teste os endpoints diretamente

---

## 🧪 Testes

```powershell
# Todos os testes
python manage.py test

# Por app
python manage.py test usuarios
python manage.py test restaurantes
python manage.py test mesas
python manage.py test reservas
```

---

## Estrutura do Projeto

```
Backend/
├── reserveaqui/
│   ├── manage.py
│   ├── reserveaqui/              # Configurações principais
│   │   ├── settings.py           
│   │   ├── urls.py               
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── usuarios/                 
│   │   ├── models.py             
│   │   ├── views.py              
│   │   ├── serializers.py        
│   │   ├── permissions.py        
│   │   └── tests.py              
│   │
│   ├── restaurantes/             
│   │   ├── models.py             
│   │   ├── views.py              
│   │   ├── serializers.py        
│   │   ├── permissions.py        
│   │   └── tests.py              
│   │
│   ├── mesas/                    
│   │   ├── models.py             
│   │   ├── views.py              
│   │   ├── serializers.py        
│   │   └── tests.py             
│   │
│   └── reservas/                 
│       ├── models.py             
│       ├── views.py              
│       ├── serializers.py        
│       ├── admin.py             
│       ├── reports.py            
│       └── tests.py              
│
└── requirements.txt              # Dependências Python
```

---

## Email (Password Recovery)

**Desenvolvimento**: Imprime email no console
```
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

**Produção**: Configurar SMTP (exemplo Gmail):
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'seu_email@gmail.com'
EMAIL_HOST_PASSWORD = 'sua_senha_de_app'
```

---

## Papéis e Permissões

| Papel | Permissões |
|-------|-----------|
| **admin_sistema** | Acesso total a todos recursos |
| **admin_secundario** | Gerenciar restaurantes e equipe |
| **funcionario** | Gerenciar mesas e reservas do restaurante |
| **cliente** | Criar e visualizar próprias reservas |

---

## Admin Panel

Acesse: `http://127.0.0.1:8000/admin/`

Gerenciar:
- Usuários e Papéis
- Restaurantes e Equipes
- Mesas e Status
- Reservas e Notificações
- Tokens de Recuperação de Senha

---
