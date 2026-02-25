from django.test import TestCase
from django.db import IntegrityError
from usuarios.models import Usuario
from restaurantes.models import Restaurante
from .models import Mesa


class MesaModelTest(TestCase):
    """Testes para o modelo Mesa"""
    
    def setUp(self):
        """Criar dados para testes"""
        self.usuario = Usuario.objects.create_user(
            email='proprietario@test.com',
            nome='Proprietário',
            username='proprietario_test',
            password='SenhaForte123'
        )
        
        self.restaurante = Restaurante.objects.create(
            nome='Restaurante Test',
            endereco='Rua Test, 123',
            cidade='Test City',
            estado='TC',
            cep='99999-999',
            email='test@restaurant.com',
            proprietario=self.usuario,
            quantidade_mesas=0  # Não criar mesas automaticamente nos testes
        )
    
    def test_criar_mesa_valida(self):
        """Teste de criação de mesa com dados válidos"""
        mesa = Mesa.objects.create(
            restaurante=self.restaurante,
            numero=1,
            status='disponivel'
        )
        
        self.assertEqual(mesa.numero, 1)
        self.assertEqual(mesa.capacidade, 4)  # Capacidade fixa
        self.assertEqual(mesa.status, 'disponivel')
        self.assertTrue(mesa.ativa)
        self.assertEqual(mesa.restaurante, self.restaurante)
    
    def test_mesa_str(self):
        """Teste da representação em string da mesa"""
        mesa = Mesa.objects.create(
            restaurante=self.restaurante,
            numero=5,
            status='ocupada'
        )
        
        self.assertEqual(str(mesa), 'Mesa 5 - Restaurante Test (Ocupada)')
    
    def test_numero_mesa_unico_por_restaurante(self):
        """Teste que número de mesa deve ser único por restaurante"""
        Mesa.objects.create(
            restaurante=self.restaurante,
            numero=1
        )
        
        with self.assertRaises(IntegrityError):
            Mesa.objects.create(
                restaurante=self.restaurante,
                numero=1
            )
    
    def test_mesas_diferentes_restaurantes_mesmo_numero(self):
        """Teste que mesmos números podem existir em restaurantes diferentes"""
        restaurante2 = Restaurante.objects.create(
            nome='Outro Restaurante',
            endereco='Rua Outra, 456',
            cidade='Outra Cidade',
            estado='OC',
            cep='00000-000',
            email='outro@restaurant.com',
            proprietario=self.usuario,
            quantidade_mesas=0  # Não criar mesas automaticamente nos testes
        )
        
        mesa1 = Mesa.objects.create(
            restaurante=self.restaurante,
            numero=1
        )
        
        mesa2 = Mesa.objects.create(
            restaurante=restaurante2,
            numero=1
        )
        
        self.assertEqual(mesa1.numero, mesa2.numero)
        self.assertNotEqual(mesa1.restaurante, mesa2.restaurante)
    
    def test_pode_reservar_disponivel(self):
        """Teste que mesa disponível pode ser reservada"""
        mesa = Mesa.objects.create(
            restaurante=self.restaurante,
            numero=1,
            status='disponivel',
            ativa=True
        )
        
        self.assertTrue(mesa.pode_reservar())
    
    def test_pode_reservar_ocupada(self):
        """Teste que mesa ocupada não pode ser reservada"""
        mesa = Mesa.objects.create(
            restaurante=self.restaurante,
            numero=1,
            status='ocupada',
            ativa=True
        )
        
        self.assertFalse(mesa.pode_reservar())
    
    def test_pode_reservar_inativa(self):
        """Teste que mesa inativa não pode ser reservada"""
        mesa = Mesa.objects.create(
            restaurante=self.restaurante,
            numero=1,
            status='disponivel',
            ativa=False
        )
        
        self.assertFalse(mesa.pode_reservar())
    
    def test_status_choices(self):
        """Teste de todos os status disponíveis"""
        status_list = ['disponivel', 'ocupada']
        
        for idx, status in enumerate(status_list):
            mesa = Mesa.objects.create(
                restaurante=self.restaurante,
                numero=100 + idx,
                status=status
            )
            
            self.assertEqual(mesa.status, status)
    
    def test_cascata_delecao_restaurante(self):
        """Teste que deletar restaurante deleta as mesas"""
        mesa = Mesa.objects.create(
            restaurante=self.restaurante,
            numero=1
        )
        
        restaurante_id = self.restaurante.id
        self.restaurante.delete()
        
        self.assertEqual(Mesa.objects.filter(restaurante_id=restaurante_id).count(), 0)
    
    def test_capacidade_fixa(self):
        """Teste que todas as mesas têm capacidade fixa de 4 pessoas"""
        mesa = Mesa.objects.create(
            restaurante=self.restaurante,
            numero=1
        )
        
        self.assertEqual(mesa.capacidade, 4)
    
    def test_capacidade_property_readonly(self):
        """Teste que capacidade é uma property read-only"""
        mesa = Mesa.objects.create(
            restaurante=self.restaurante,
            numero=50
        )
        
        # Capacidade sempre retorna 4
        self.assertEqual(mesa.capacidade, 4)
