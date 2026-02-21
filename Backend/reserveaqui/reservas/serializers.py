from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta, datetime
import math
from .models import Reserva, ReservaMesa
from mesas.models import Mesa
from restaurantes.models import Restaurante


class ReservaMesaSerializer(serializers.ModelSerializer):
    """Serializer para o relacionamento Reserva-Mesa"""
    mesa_numero = serializers.IntegerField(source='mesa.numero', read_only=True)
    mesa_capacidade = serializers.IntegerField(source='mesa.capacidade', read_only=True)
    
    class Meta:
        model = ReservaMesa
        fields = ['mesa', 'mesa_numero', 'mesa_capacidade', 'data_vinculacao']
        read_only_fields = ['data_vinculacao']


class ReservaSerializer(serializers.ModelSerializer):
    """Serializer completo para Reserva com todos os detalhes"""
    restaurante_nome = serializers.CharField(source='restaurante.nome', read_only=True)
    usuario_nome = serializers.CharField(source='usuario.nome', read_only=True)
    mesas_vinculadas = ReservaMesaSerializer(source='reservamesa_set', many=True, read_only=True)
    mesas_necessarias = serializers.SerializerMethodField()
    pode_cancelar = serializers.SerializerMethodField()
    
    class Meta:
        model = Reserva
        fields = [
            'id', 'restaurante', 'restaurante_nome', 'usuario', 'usuario_nome',
            'data_reserva', 'horario', 'quantidade_pessoas',
            'nome_cliente', 'telefone_cliente', 'email_cliente', 'observacoes',
            'status', 'mesas_vinculadas', 'mesas_necessarias', 'pode_cancelar',
            'data_criacao', 'data_atualizacao'
        ]
        read_only_fields = ['id', 'usuario', 'status', 'data_criacao', 'data_atualizacao']
    
    def get_mesas_necessarias(self, obj):
        """Calcula quantas mesas são necessárias"""
        return obj.calcular_mesas_necessarias()
    
    def get_pode_cancelar(self, obj):
        """Verifica se a reserva pode ser cancelada"""
        return obj.pode_cancelar()


class ReservaListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listagem de reservas"""
    restaurante_nome = serializers.CharField(source='restaurante.nome', read_only=True)
    total_mesas = serializers.SerializerMethodField()
    
    class Meta:
        model = Reserva
        fields = [
            'id', 'restaurante', 'restaurante_nome',
            'data_reserva', 'horario', 'quantidade_pessoas',
            'nome_cliente', 'status', 'total_mesas'
        ]
    
    def get_total_mesas(self, obj):
        """Retorna total de mesas alocadas"""
        return obj.mesas.count()


class ReservaCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para criação e atualização de reservas com validações"""
    
    class Meta:
        model = Reserva
        fields = [
            'restaurante', 'data_reserva', 'horario', 'quantidade_pessoas',
            'nome_cliente', 'telefone_cliente', 'email_cliente', 'observacoes'
        ]
    
    def validate(self, data):
        """Validações gerais"""
        # Validar data e horário não podem ser no passado
        data_reserva = data.get('data_reserva')
        horario = data.get('horario')
        
        if data_reserva and horario:
            data_hora_reserva = timezone.make_aware(
                datetime.combine(data_reserva, horario)
            )
            limite_minimo = timezone.now() + timedelta(hours=2)
            
            if data_hora_reserva < limite_minimo:
                raise serializers.ValidationError(
                    'Reservas devem ser feitas com no mínimo 2 horas de antecedência.'
                )
        
        # Validar quantidade de pessoas
        quantidade_pessoas = data.get('quantidade_pessoas')
        if quantidade_pessoas and quantidade_pessoas < 1:
            raise serializers.ValidationError(
                {'quantidade_pessoas': 'A quantidade de pessoas deve ser maior que zero.'}
            )
        
        return data
    
    def validate_restaurante(self, value):
        """Validar que o restaurante está ativo"""
        if not value.ativo:
            raise serializers.ValidationError('Este restaurante não está disponível para reservas.')
        return value
    
    def _verificar_disponibilidade(self, restaurante, data_reserva, horario, quantidade_pessoas, reserva_atual=None):
        """
        Verifica se há mesas disponíveis para a reserva.
        RF06, RN01: Impedir reservas de uma mesma mesa no mesmo horário
        """
        # Calcular quantas mesas são necessárias
        mesas_necessarias = math.ceil(quantidade_pessoas / 4)
        
        # Buscar reservas conflitantes (±1h)
        data_hora = datetime.combine(data_reserva, horario)
        inicio = (data_hora - timedelta(hours=1)).time()
        fim = (data_hora + timedelta(hours=1)).time()
        
        # Buscar reservas conflitantes
        reservas_conflitantes = Reserva.objects.filter(
            restaurante=restaurante,
            data_reserva=data_reserva,
            horario__gte=inicio,
            horario__lte=fim,
            status__in=['pendente', 'confirmada']
        )
        
        # Excluir a reserva atual em caso de edição
        if reserva_atual:
            reservas_conflitantes = reservas_conflitantes.exclude(id=reserva_atual.id)
        
        # Obter IDs das mesas ocupadas
        mesas_ocupadas_ids = ReservaMesa.objects.filter(
            reserva__in=reservas_conflitantes
        ).values_list('mesa_id', flat=True)
        
        # Buscar mesas disponíveis
        mesas_disponiveis = Mesa.objects.filter(
            restaurante=restaurante,
            ativa=True,
            status='disponivel'
        ).exclude(id__in=mesas_ocupadas_ids)
        
        if mesas_disponiveis.count() < mesas_necessarias:
            raise serializers.ValidationError(
                f'Não há mesas suficientes disponíveis. '
                f'Necessárias: {mesas_necessarias}, Disponíveis: {mesas_disponiveis.count()}'
            )
        
        return list(mesas_disponiveis[:mesas_necessarias])
    
    def create(self, validated_data):
        """
        Cria uma reserva e aloca automaticamente as mesas necessárias.
        RF05: Permitir realizar reservas
        """
        restaurante = validated_data['restaurante']
        data_reserva = validated_data['data_reserva']
        horario = validated_data['horario']
        quantidade_pessoas = validated_data['quantidade_pessoas']
        
        # Verificar disponibilidade e obter mesas disponíveis
        mesas_disponiveis = self._verificar_disponibilidade(
            restaurante, data_reserva, horario, quantidade_pessoas
        )
        
        # Adicionar usuário se autenticado
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['usuario'] = request.user
        
        # Criar a reserva
        reserva = Reserva.objects.create(**validated_data)
        
        # Alocar mesas automaticamente
        for mesa in mesas_disponiveis:
            ReservaMesa.objects.create(reserva=reserva, mesa=mesa)
        
        return reserva
    
    def update(self, instance, validated_data):
        """
        Atualiza uma reserva com validações.
        RF05: Permitir editar reservas
        """
        # Validar se a reserva pode ser editada
        if instance.status in ['cancelada', 'concluida']:
            raise serializers.ValidationError(
                'Não é possível editar reservas canceladas ou concluídas.'
            )
        
        # Validar se a edição está sendo feita com antecedência
        data_hora_reserva = timezone.make_aware(
            datetime.combine(instance.data_reserva, instance.horario)
        )
        limite_edicao = data_hora_reserva - timedelta(hours=2)
        
        if timezone.now() > limite_edicao:
            raise serializers.ValidationError(
                'Não é possível editar reservas com menos de 2 horas de antecedência.'
            )
        
        # Se houver mudança em data, horário ou quantidade de pessoas, realocar mesas
        mudou_parametros = (
            'data_reserva' in validated_data or 
            'horario' in validated_data or 
            'quantidade_pessoas' in validated_data
        )
        
        if mudou_parametros:
            restaurante = validated_data.get('restaurante', instance.restaurante)
            data_reserva = validated_data.get('data_reserva', instance.data_reserva)
            horario = validated_data.get('horario', instance.horario)
            quantidade_pessoas = validated_data.get('quantidade_pessoas', instance.quantidade_pessoas)
            
            # Verificar disponibilidade
            mesas_disponiveis = self._verificar_disponibilidade(
                restaurante, data_reserva, horario, quantidade_pessoas, instance
            )
            
            # Remover mesas antigas
            ReservaMesa.objects.filter(reserva=instance).delete()
            
            # Alocar novas mesas
            for mesa in mesas_disponiveis:
                ReservaMesa.objects.create(reserva=instance, mesa=mesa)
        
        # Atualizar campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance
