from rest_framework import serializers
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Usuario"""
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = Usuario
        fields = ('id', 'email', 'nome', 'tipo', 'password', 'password_confirm', 'date_joined')
        read_only_fields = ('id', 'date_joined')

    def validate(self, data):
        """Validar se as senhas batem"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password': 'As senhas não correspondem.'})
        return data

    def create(self, validated_data):
        """Criar novo usuário com a senha"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        usuario = Usuario.objects.create_user(**validated_data, password=password)
        return usuario
