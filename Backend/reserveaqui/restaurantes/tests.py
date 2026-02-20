from django.test import TestCase
from django.db import IntegrityError
from usuarios.models import Usuario, Papel
from .models import Restaurante, RestauranteUsuario


class RestauranteModelTest(TestCase):
    """Testes para o modelo Restaurante"""
    
    def setUp(self):
        """Criar um usuário para ser proprietário do restaurante"""
        self.usuario = Usuario.objects.create_user(
            email='proprietario@restaurant.com',
            nome='João Proprietário',
            username='joao_prop',
            password='SenhaForte123'
        )
    
    def test_criar_restaurante_valido(self):
        """Teste de criação de um restaurante com dados válidos"""
        restaurante = Restaurante.objects.create(
            nome='Restaurante Delícia',
            descricao='Melhor comida da cidade',
            endereco='Rua das Flores, 123',
            cidade='Fortaleza',
            estado='CE',
            cep='60000-000',
            telefone='(85) 3333-3333',
            email='contato@delicia.com',
            proprietario=self.usuario
        )
        
        self.assertEqual(restaurante.nome, 'Restaurante Delícia')
        self.assertEqual(restaurante.cidade, 'Fortaleza')
        self.assertEqual(restaurante.proprietario, self.usuario)
        self.assertTrue(restaurante.ativo)
        self.assertIsNotNone(restaurante.data_criacao)
    
    def test_restaurante_str(self):
        """Teste da representação em string do restaurante"""
        restaurante = Restaurante.objects.create(
            nome='Pizza House',
            endereco='Rua A, 1',
            cidade='São Paulo',
            estado='SP',
            cep='01000-000',
            email='pizza@house.com',
            proprietario=self.usuario
        )
        
        self.assertEqual(str(restaurante), 'Pizza House (São Paulo)')
    
    def test_email_restaurante_unico(self):
        """Teste que email de restaurante deve ser único"""
        Restaurante.objects.create(
            nome='Rest 1',
            endereco='Rua 1',
            cidade='Cidade 1',
            estado='ST',
            cep='00000-000',
            email='unico@rest.com',
            proprietario=self.usuario
        )
        
        with self.assertRaises(IntegrityError):
            Restaurante.objects.create(
                nome='Rest 2',
                endereco='Rua 2',
                cidade='Cidade 2',
                estado='ST',
                cep='00000-001',
                email='unico@rest.com',
                proprietario=self.usuario
            )


class RestauranteUsuarioModelTest(TestCase):
    """Testes para o modelo RestauranteUsuario"""
    
    def setUp(self):
        """Criar dados para testes"""
        self.proprietario = Usuario.objects.create_user(
            email='proprietario@test.com',
            nome='Proprietário',
            username='prop_test',
            password='SenhaForte123'
        )
        
        self.funcionario = Usuario.objects.create_user(
            email='funcionario@test.com',
            nome='Funcionário',
            username='func_test',
            password='SenhaForte123'
        )
        
        self.restaurante = Restaurante.objects.create(
            nome='Test Restaurant',
            endereco='Rua Test',
            cidade='Test City',
            estado='TC',
            cep='99999-999',
            email='test@restaurant.com',
            proprietario=self.proprietario
        )
    
    def test_vincular_usuario_ao_restaurante(self):
        """Teste de vinculação de usuário ao restaurante"""
        vinculo = RestauranteUsuario.objects.create(
            restaurante=self.restaurante,
            usuario=self.funcionario,
            papel='funcionario'
        )
        
        self.assertEqual(vinculo.usuario, self.funcionario)
        self.assertEqual(vinculo.restaurante, self.restaurante)
        self.assertEqual(vinculo.papel, 'funcionario')
        self.assertIsNotNone(vinculo.data_vinculacao)
    
    def test_restaurante_usuario_str(self):
        """Teste da representação em string de RestauranteUsuario"""
        vinculo = RestauranteUsuario.objects.create(
            restaurante=self.restaurante,
            usuario=self.funcionario,
            papel='funcionario'
        )
        
        self.assertEqual(
            str(vinculo),
            'Funcionário - Test Restaurant (Funcionário)'
        )
    
    def test_unique_together_restaurante_usuario(self):
        """Teste que a combinação restaurante+usuario deve ser única"""
        RestauranteUsuario.objects.create(
            restaurante=self.restaurante,
            usuario=self.funcionario,
            papel='funcionario'
        )
        
        with self.assertRaises(IntegrityError):
            RestauranteUsuario.objects.create(
                restaurante=self.restaurante,
                usuario=self.funcionario,
                papel='admin_secundario'
            )
    
    def test_papeis_disponiveis(self):
        """Teste de diferentes papéis disponíveis"""
        papeis = ['admin_secundario', 'funcionario', 'cliente']
        
        for idx, papel in enumerate(papeis):
            usuario = Usuario.objects.create_user(
                email=f'user{idx}@test.com',
                nome=f'User {idx}',
                username=f'user_{idx}',
                password='SenhaForte123'
            )
            
            vinculo = RestauranteUsuario.objects.create(
                restaurante=self.restaurante,
                usuario=usuario,
                papel=papel
            )
            
            self.assertEqual(vinculo.papel, papel)
            self.assertEqual(vinculo.get_papel_display(), {'admin_secundario': 'Admin Secundário', 'funcionario': 'Funcionário', 'cliente': 'Cliente'}[papel])
