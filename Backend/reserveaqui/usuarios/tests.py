from django.test import TestCase
from django.db import IntegrityError
from django.contrib.auth import authenticate
from .models import Usuario, Papel, UsuarioPapel
from .validators import validar_forca_senha


class PapelModelTest(TestCase):
    """Testes para o modelo Papel"""
    
    def test_criar_papel_valido(self):
        """Teste de criação de papel com dados válidos"""
        papel = Papel.objects.create(
            tipo='admin_sistema',
            descricao='Administrador do Sistema'
        )
        
        self.assertEqual(papel.tipo, 'admin_sistema')
        self.assertEqual(papel.get_tipo_display(), 'Admin do Sistema')
        self.assertIsNotNone(papel.data_criacao)
    
    def test_tipo_papel_unico(self):
        """Teste que tipo de papel deve ser único"""
        Papel.objects.create(tipo='admin_sistema', descricao='Admin')
        
        with self.assertRaises(IntegrityError):
            Papel.objects.create(tipo='admin_sistema', descricao='Outro Admin')
    
    def test_papel_str(self):
        """Teste da representação em string do papel"""
        papel = Papel.objects.create(tipo='cliente', descricao='Usuário Cliente')
        self.assertEqual(str(papel), 'Cliente')
    
    def test_tipos_papel_disponiveis(self):
        """Teste que todos os tipos de papel podem ser criados"""
        tipos_esperados = [
            'admin_sistema',
            'admin_secundario',
            'funcionario',
            'cliente'
        ]
        
        for tipo in tipos_esperados:
            papel = Papel.objects.create(tipo=tipo)
            self.assertEqual(Papel.objects.filter(tipo=tipo).count(), 1)


class UsuarioModelTest(TestCase):
    """Testes para o modelo Usuario"""
    
    def setUp(self):
        """Criar papéis para os testes"""
        self.papel_cliente = Papel.objects.create(tipo='cliente')
        self.papel_admin = Papel.objects.create(tipo='admin_sistema')
    
    def test_criar_usuario_valido(self):
        """Teste de criação de usuário com dados válidos"""
        usuario = Usuario.objects.create_user(
            email='joao@example.com',
            nome='João Silva',
            username='joao_silva',
            password='SenhaForte123'
        )
        
        self.assertEqual(usuario.email, 'joao@example.com')
        self.assertEqual(usuario.nome, 'João Silva')
        self.assertTrue(usuario.check_password('SenhaForte123'))
    
    def test_email_usuario_unico(self):
        """Teste que email de usuário deve ser único"""
        Usuario.objects.create_user(
            email='unico@example.com',
            nome='Usuario 1',
            username='user1',
            password='SenhaForte123'
        )
        
        with self.assertRaises(IntegrityError):
            Usuario.objects.create_user(
                email='unico@example.com',
                nome='Usuario 2',
                username='user2',
                password='SenhaForte123'
            )
    
    def test_usuario_str(self):
        """Teste da representação em string do usuário"""
        usuario = Usuario.objects.create_user(
            email='maria@example.com',
            nome='Maria Santos',
            username='maria_santos',
            password='SenhaForte123'
        )
        
        self.assertEqual(str(usuario), 'Maria Santos (maria@example.com)')
    
    def test_email_como_username_field(self):
        """Teste que email é usado como USERNAME_FIELD"""
        usuario = Usuario.objects.create_user(
            email='teste@example.com',
            nome='Teste',
            username='teste_user',
            password='SenhaForte123'
        )
        
        # Autenticar com email
        auth_user = authenticate(username='teste@example.com', password='SenhaForte123')
        self.assertEqual(auth_user, usuario)
    
    def test_usuario_tem_papel_true(self):
        """Teste do método tem_papel() quando usuário tem papel"""
        usuario = Usuario.objects.create_user(
            email='admin@example.com',
            nome='Admin User',
            username='admin_user',
            password='SenhaForte123'
        )
        usuario.papeis.add(self.papel_admin)
        
        self.assertTrue(usuario.tem_papel('admin_sistema'))
    
    def test_usuario_tem_papel_false(self):
        """Teste do método tem_papel() quando usuário não tem papel"""
        usuario = Usuario.objects.create_user(
            email='cliente@example.com',
            nome='Cliente User',
            username='cliente_user',
            password='SenhaForte123'
        )
        usuario.papeis.add(self.papel_cliente)
        
        self.assertFalse(usuario.tem_papel('admin_sistema'))
    
    def test_usuario_multiplos_papeis(self):
        """Teste que usuário pode ter múltiplos papéis"""
        usuario = Usuario.objects.create_user(
            email='multiplo@example.com',
            nome='Multi Role User',
            username='multi_user',
            password='SenhaForte123'
        )
        
        usuario.papeis.add(self.papel_cliente, self.papel_admin)
        
        self.assertEqual(usuario.papeis.count(), 2)
        self.assertTrue(usuario.tem_papel('cliente'))
        self.assertTrue(usuario.tem_papel('admin_sistema'))


class UsuarioPapelModelTest(TestCase):
    """Testes para o modelo UsuarioPapel (intermediário)"""
    
    def setUp(self):
        """Criar dados para testes"""
        self.usuario = Usuario.objects.create_user(
            email='usuario@example.com',
            nome='Usuario Test',
            username='usuario_test',
            password='SenhaForte123'
        )
        
        self.papel = Papel.objects.create(tipo='funcionario')
    
    def test_criar_usuario_papel_valido(self):
        """Teste de criação de relacionamento usuario-papel"""
        usuario_papel = UsuarioPapel.objects.create(
            usuario=self.usuario,
            papel=self.papel
        )
        
        self.assertEqual(usuario_papel.usuario, self.usuario)
        self.assertEqual(usuario_papel.papel, self.papel)
        self.assertIsNotNone(usuario_papel.data_atribuicao)
    
    def test_usuario_papel_str(self):
        """Teste da representação em string de UsuarioPapel"""
        usuario_papel = UsuarioPapel.objects.create(
            usuario=self.usuario,
            papel=self.papel
        )
        
        self.assertEqual(str(usuario_papel), 'Usuario Test - Funcionário')
    
    def test_unique_together_usuario_papel(self):
        """Teste que a combinação usuario+papel deve ser única"""
        UsuarioPapel.objects.create(usuario=self.usuario, papel=self.papel)
        
        with self.assertRaises(IntegrityError):
            UsuarioPapel.objects.create(usuario=self.usuario, papel=self.papel)
    
    def test_cascata_delecao_usuario(self):
        """Teste que deletar usuário deleta relacionamentos com papéis"""
        UsuarioPapel.objects.create(usuario=self.usuario, papel=self.papel)
        
        usuario_id = self.usuario.id
        self.usuario.delete()
        
        self.assertEqual(UsuarioPapel.objects.filter(usuario_id=usuario_id).count(), 0)
    
    def test_cascata_delecao_papel(self):
        """Teste que deletar papel deleta relacionamentos com usuários"""
        usuario_papel = UsuarioPapel.objects.create(usuario=self.usuario, papel=self.papel)
        
        papel_id = self.papel.id
        self.papel.delete()
        
        self.assertEqual(UsuarioPapel.objects.filter(papel_id=papel_id).count(), 0)


class ValidadorForcaSenhaTest(TestCase):
    """Testes para o validador de força de senha"""
    
    def test_senha_valida(self):
        """Teste com senha válida"""
        try:
            validar_forca_senha('SenhaForte123')
            # Se não lançar exceção, passou
        except Exception:
            self.fail('Senha válida lançou exceção')
    
    def test_senha_muito_curta(self):
        """Teste com senha com menos de 8 caracteres"""
        from django.core.exceptions import ValidationError
        
        with self.assertRaises(ValidationError):
            validar_forca_senha('Abc12')
    
    def test_senha_sem_maiuscula(self):
        """Teste com senha sem letra maiúscula"""
        from django.core.exceptions import ValidationError
        
        with self.assertRaises(ValidationError):
            validar_forca_senha('senhafraco123')
    
    def test_senha_sem_numero(self):
        """Teste com senha sem número"""
        from django.core.exceptions import ValidationError
        
        with self.assertRaises(ValidationError):
            validar_forca_senha('SenhaFraco')
    
    def test_senha_apenas_maiuscula_numero(self):
        """Teste com senha válida com apenas maiúscula e número"""
        try:
            validar_forca_senha('SENHAFORTE1')
            # Se não lançar exceção, passou
        except Exception:
            self.fail('Senha válida lançou exceção')
