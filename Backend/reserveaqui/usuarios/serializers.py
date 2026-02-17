from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Usuario, Papel
from .validators import validar_forca_senha


class PapelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Papel
        fields = ('id', 'tipo', 'get_tipo_display')
        read_only_fields = ('id', 'get_tipo_display')


class UsuarioSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Usuario"""
    papeis = PapelSerializer(many=True, read_only=True)
    papeis_ids = serializers.PrimaryKeyRelatedField(
        queryset=Papel.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='papeis'
    )
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'},
        validators=[validar_forca_senha]
    )
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = Usuario
        fields = ('id', 'email', 'nome', 'papeis', 'papeis_ids', 'password', 'password_confirm', 'date_joined')
        read_only_fields = ('id', 'date_joined')

    def validate(self, data):
        """Validar se as senhas batem"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password': 'As senhas não correspondem.'})
        return data

    def create(self, validated_data):
        """Criar novo usuário com a senha e papéis"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        papeis = validated_data.pop('papeis', [])
        
        # Gerar username a partir do email
        email = validated_data.get('email')
        username = email.split('@')[0]
        
        usuario = Usuario.objects.create_user(username=username, **validated_data, password=password)
        
        # Adicionar papéis
        for papel in papeis:
            usuario.papeis.add(papel)
        
        return usuario


class LoginSerializer(serializers.Serializer):
    """Serializer para login de usuário com email e senha"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        """Autenticar o usuário"""
        email = data.get('email')
        password = data.get('password')

        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError({'email': 'Usuário não encontrado.'})

        if not usuario.check_password(password):
            raise serializers.ValidationError({'password': 'Senha incorreta.'})

        data['usuario'] = usuario
        return data
