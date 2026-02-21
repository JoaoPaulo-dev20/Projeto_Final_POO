from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from .models import Reserva, ReservaMesa
from .serializers import (
    ReservaSerializer,
    ReservaListSerializer,
    ReservaCreateUpdateSerializer
)
from .permissions import IsOwnerOrAdminForReservas


class ReservaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de reservas.
    
    Implementa:
    - RF05: Criar, editar e cancelar reservas
    - RF06: Validação de conflito de mesas
    - RF07: Confirmação de reserva
    - RF12: Listar reservas do usuário
    - RN01: Impedir mesma mesa no mesmo horário
    - RN03: Liberar mesas ao cancelar
    """
    
    queryset = Reserva.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrAdminForReservas]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['restaurante', 'status', 'data_reserva']
    search_fields = ['nome_cliente', 'telefone_cliente', 'email_cliente']
    ordering_fields = ['data_reserva', 'horario', 'data_criacao']
    ordering = ['-data_reserva', '-horario']
    
    def get_serializer_class(self):
        """Retorna o serializer apropriado para cada ação"""
        if self.action == 'list':
            return ReservaListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ReservaCreateUpdateSerializer
        return ReservaSerializer
    
    def get_queryset(self):
        """
        RF12: Filtrar reservas por usuário.
        - Admins veem todas as reservas
        - Usuários comuns veem apenas suas próprias reservas
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # Verificar se é admin
        is_admin = user.usuariopapel_set.filter(
            papel__nome__in=['admin_sistema', 'admin_secundario']
        ).exists()
        
        if is_admin:
            return queryset
        
        # Usuário comum vê apenas suas reservas
        return queryset.filter(usuario=user)
    
    def create(self, request, *args, **kwargs):
        """
        RF05: Criar reserva com alocação automática de mesas.
        RF06: Validação de conflito.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Retornar com serializer completo
        output_serializer = ReservaSerializer(serializer.instance)
        headers = self.get_success_headers(output_serializer.data)
        
        return Response(
            {
                'message': 'Reserva criada com sucesso! Aguardando confirmação do restaurante.',
                'reserva': output_serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    def update(self, request, *args, **kwargs):
        """RF05: Editar reserva com validações"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Retornar com serializer completo
        output_serializer = ReservaSerializer(serializer.instance)
        
        return Response({
            'message': 'Reserva atualizada com sucesso!',
            'reserva': output_serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        """
        RF07: Confirmar reserva.
        Apenas admins podem confirmar.
        """
        # Verificar se é admin
        is_admin = request.user.usuariopapel_set.filter(
            papel__nome__in=['admin_sistema', 'admin_secundario']
        ).exists()
        
        if not is_admin:
            return Response(
                {'error': 'Apenas administradores podem confirmar reservas.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reserva = self.get_object()
        
        # Validar status atual
        if reserva.status == 'confirmada':
            return Response(
                {'error': 'Esta reserva já está confirmada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if reserva.status == 'cancelada':
            return Response(
                {'error': 'Não é possível confirmar uma reserva cancelada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if reserva.status == 'concluida':
            return Response(
                {'error': 'Esta reserva já foi concluída.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Confirmar reserva
        reserva.status = 'confirmada'
        reserva.save()
        
        # TODO: RF07 - Aqui seria enviada uma notificação ao cliente
        # Implementar sistema de notificações (email, SMS, etc)
        
        serializer = ReservaSerializer(reserva)
        return Response({
            'message': 'Reserva confirmada com sucesso! Cliente será notificado.',
            'reserva': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        RF05: Cancelar reserva.
        RN03: Liberar mesas automaticamente ao cancelar.
        """
        reserva = self.get_object()
        
        # Verificar se pode cancelar
        if reserva.status == 'cancelada':
            return Response(
                {'error': 'Esta reserva já está cancelada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if reserva.status == 'concluida':
            return Response(
                {'error': 'Não é possível cancelar uma reserva já concluída.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not reserva.pode_cancelar():
            return Response(
                {'error': 'Não é possível cancelar reservas com menos de 2 horas de antecedência.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # RN03: Liberar mesas automaticamente
        ReservaMesa.objects.filter(reserva=reserva).delete()
        
        # Atualizar status
        reserva.status = 'cancelada'
        reserva.save()
        
        serializer = ReservaSerializer(reserva)
        return Response({
            'message': 'Reserva cancelada com sucesso! As mesas foram liberadas.',
            'reserva': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def concluir(self, request, pk=None):
        """
        Marca a reserva como concluída.
        Apenas admins podem concluir.
        """
        # Verificar se é admin
        is_admin = request.user.usuariopapel_set.filter(
            papel__nome__in=['admin_sistema', 'admin_secundario']
        ).exists()
        
        if not is_admin:
            return Response(
                {'error': 'Apenas administradores podem concluir reservas.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reserva = self.get_object()
        
        # Validar status
        if reserva.status != 'confirmada':
            return Response(
                {'error': 'Apenas reservas confirmadas podem ser concluídas.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Concluir reserva
        reserva.status = 'concluida'
        reserva.save()
        
        serializer = ReservaSerializer(reserva)
        return Response({
            'message': 'Reserva concluída com sucesso!',
            'reserva': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def minhas_reservas(self, request):
        """
        RF12: Listar reservas do usuário autenticado.
        Endpoint conveniente para o usuário.
        """
        queryset = self.get_queryset().filter(usuario=request.user)
        
        # Aplicar filtros
        queryset = self.filter_queryset(queryset)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReservaListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ReservaListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def estatisticas(self, request):
        """
        Estatísticas básicas de reservas.
        Apenas para admins.
        """
        # Verificar se é admin
        is_admin = request.user.usuariopapel_set.filter(
            papel__nome__in=['admin_sistema', 'admin_secundario']
        ).exists()
        
        if not is_admin:
            return Response(
                {'error': 'Apenas administradores podem visualizar estatísticas.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        stats = {
            'total_reservas': queryset.count(),
            'pendentes': queryset.filter(status='pendente').count(),
            'confirmadas': queryset.filter(status='confirmada').count(),
            'canceladas': queryset.filter(status='cancelada').count(),
            'concluidas': queryset.filter(status='concluida').count(),
            'hoje': queryset.filter(data_reserva=timezone.now().date()).count(),
        }
        
        return Response(stats)
