"""
Módulo de Relatórios de ocupação e movimentação.
Endpoints de relatório de ocupação, horários mais movimentados e estatísticas por período.
"""

from django.db.models import Count, Q, F, Case, When, DecimalField, Avg
from django.utils import timezone
from datetime import datetime, timedelta, date
from rest_framework import serializers
from .models import Reserva, ReservaMesa


class RelatorioOcupacaoSerializer(serializers.Serializer):
    """Serializer para relatório de ocupação de mesas"""
    restaurante_id = serializers.IntegerField()
    restaurante_nome = serializers.CharField()
    data = serializers.DateField()
    total_mesas = serializers.IntegerField()
    mesas_ocupadas = serializers.IntegerField()
    percentual_ocupacao = serializers.DecimalField(max_digits=5, decimal_places=2)
    reservas_confirmadas = serializers.IntegerField()
    reservas_pendentes = serializers.IntegerField()


class HorarioMovimentadoSerializer(serializers.Serializer):
    """Serializer para horários mais movimentados"""
    restaurante_id = serializers.IntegerField()
    restaurante_nome = serializers.CharField()
    horario = serializers.TimeField()
    total_reservas = serializers.IntegerField()
    pessoas_total = serializers.IntegerField()
    taxa_confirmacao = serializers.DecimalField(max_digits=5, decimal_places=2)


class EstatisticasSerieSerializer(serializers.Serializer):
    """Serializer para estatísticas por período"""
    periodo = serializers.CharField()
    total_reservas = serializers.IntegerField()
    reservas_confirmadas = serializers.IntegerField()
    reservas_canceladas = serializers.IntegerField()
    reservas_pendentes = serializers.IntegerField()
    pessoas_total = serializers.IntegerField()
    ticket_medio = serializers.DecimalField(max_digits=10, decimal_places=2)
    taxa_cancelamento = serializers.DecimalField(max_digits=5, decimal_places=2)


class RelatorioHelper:
    """Helper para gerar relatórios"""
    
    @staticmethod
    def gerar_relatorio_ocupacao(restaurante_id=None, data_inicio=None, data_fim=None):
        """
        Gera relatório de ocupação de mesas.
        Calcula percentual de ocupação por restaurante/data.
        """
        from restaurantes.models import Restaurante
        from mesas.models import Mesa
        
        # Filtros padrão
        if not data_inicio:
            data_inicio = timezone.now().date()
        if not data_fim:
            data_fim = data_inicio
        
        # Buscar restaurantes
        restaurantes_qs = Restaurante.objects.all()
        if restaurante_id:
            restaurantes_qs = restaurantes_qs.filter(id=restaurante_id)
        
        relatorio = []
        
        for restaurante in restaurantes_qs:
            # Calcular total de mesas
            total_mesas = Mesa.objects.filter(restaurante=restaurante, ativa=True).count()
            
            if total_mesas == 0:
                continue
            
            # Iterar sobre datas
            data_atual = data_inicio
            while data_atual <= data_fim:
                # Contar reservas confirmadas para a data
                reservas_confirmadas = Reserva.objects.filter(
                    restaurante=restaurante,
                    data_reserva=data_atual,
                    status='confirmada'
                ).count()
                
                # Contar mesas ocupadas (usar ReservaMesa)
                mesas_ocupadas = ReservaMesa.objects.filter(
                    reserva__restaurante=restaurante,
                    reserva__data_reserva=data_atual,
                    reserva__status__in=['pendente', 'confirmada']
                ).values('mesa_id').distinct().count()
                
                # Contar reservas pendentes
                reservas_pendentes = Reserva.objects.filter(
                    restaurante=restaurante,
                    data_reserva=data_atual,
                    status='pendente'
                ).count()
                
                # Calcular percentual
                percentual = (mesas_ocupadas / total_mesas * 100) if total_mesas > 0 else 0
                
                relatorio.append({
                    'restaurante_id': restaurante.id,
                    'restaurante_nome': restaurante.nome,
                    'data': data_atual,
                    'total_mesas': total_mesas,
                    'mesas_ocupadas': mesas_ocupadas,
                    'percentual_ocupacao': round(percentual, 2),
                    'reservas_confirmadas': reservas_confirmadas,
                    'reservas_pendentes': reservas_pendentes,
                })
                
                data_atual += timedelta(days=1)
        
        return relatorio
    
    @staticmethod
    def gerar_relatorio_horarios_movimentados(restaurante_id=None, data_inicio=None, data_fim=None, top=10):
        """
        Gera relatório de horários mais movimentados.
        Identifica os horários com maior número de reservas.
        """
        # Filtros padrão
        if not data_inicio:
            data_inicio = timezone.now().date() - timedelta(days=30)
        if not data_fim:
            data_fim = timezone.now().date()
        
        # Buscar reservas no período
        reservas_qs = Reserva.objects.filter(
            data_reserva__gte=data_inicio,
            data_reserva__lte=data_fim,
            status__in=['pendente', 'confirmada']
        )
        
        if restaurante_id:
            reservas_qs = reservas_qs.filter(restaurante_id=restaurante_id)
        
        # Agrupar por restaurante e horário
        horarios = {}
        
        for reserva in reservas_qs:
            chave = (reserva.restaurante_id, reserva.restaurante.nome, reserva.horario)
            
            if chave not in horarios:
                horarios[chave] = {
                    'total_reservas': 0,
                    'pessoas_total': 0,
                    'confirmadas': 0,
                }
            
            horarios[chave]['total_reservas'] += 1
            horarios[chave]['pessoas_total'] += reserva.quantidade_pessoas
            
            if reserva.status == 'confirmada':
                horarios[chave]['confirmadas'] += 1
        
        # Montar resposta
        relatorio = []
        for (restaurante_id, restaurante_nome, horario), stats in horarios.items():
            taxa_confirmacao = (stats['confirmadas'] / stats['total_reservas'] * 100) if stats['total_reservas'] > 0 else 0
            
            relatorio.append({
                'restaurante_id': restaurante_id,
                'restaurante_nome': restaurante_nome,
                'horario': horario,
                'total_reservas': stats['total_reservas'],
                'pessoas_total': stats['pessoas_total'],
                'taxa_confirmacao': round(taxa_confirmacao, 2),
            })
        
        # Ordenar por total de reservas (decrescente) e retornar top
        relatorio.sort(key=lambda x: x['total_reservas'], reverse=True)
        return relatorio[:top]
    
    @staticmethod
    def gerar_relatorio_estatisticas_periodo(restaurante_id=None, data_inicio=None, data_fim=None, tipo_periodo='dia'):
        """
        Gera estatísticas por período (dia, semana, mês).
        Calcula: total, confirmadas, canceladas, pessoas, ticket médio, taxa de cancelamento.
        """
        # Filtros padrão
        if not data_inicio:
            data_inicio = timezone.now().date() - timedelta(days=30)
        if not data_fim:
            data_fim = timezone.now().date()
        
        # Buscar reservas
        reservas_qs = Reserva.objects.filter(
            data_reserva__gte=data_inicio,
            data_reserva__lte=data_fim
        )
        
        if restaurante_id:
            reservas_qs = reservas_qs.filter(restaurante_id=restaurante_id)
        
        # Agrupar por período
        stats_por_periodo = {}
        
        for reserva in reservas_qs:
            if tipo_periodo == 'dia':
                periodo_chave = str(reserva.data_reserva)
                periodo_label = reserva.data_reserva.strftime('%d/%m/%Y')
            elif tipo_periodo == 'semana':
                ano, semana, _ = reserva.data_reserva.isocalendar()
                periodo_chave = f"{ano}-W{semana:02d}"
                periodo_label = f"Semana {semana}/{ano}"
            elif tipo_periodo == 'mes':
                periodo_chave = reserva.data_reserva.strftime('%Y-%m')
                periodo_label = reserva.data_reserva.strftime('%m/%Y')
            else:
                continue
            
            if periodo_chave not in stats_por_periodo:
                stats_por_periodo[periodo_chave] = {
                    'periodo': periodo_label,
                    'total': 0,
                    'confirmadas': 0,
                    'canceladas': 0,
                    'pendentes': 0,
                    'pessoas': 0,
                }
            
            stats_por_periodo[periodo_chave]['total'] += 1
            stats_por_periodo[periodo_chave]['pessoas'] += reserva.quantidade_pessoas
            
            if reserva.status == 'confirmada':
                stats_por_periodo[periodo_chave]['confirmadas'] += 1
            elif reserva.status == 'cancelada':
                stats_por_periodo[periodo_chave]['canceladas'] += 1
            elif reserva.status == 'pendente':
                stats_por_periodo[periodo_chave]['pendentes'] += 1
        
        # Montar resposta final
        relatorio = []
        for periodo_chave, stats in stats_por_periodo.items():
            ticket_medio = (stats['pessoas'] / stats['confirmadas']) if stats['confirmadas'] > 0 else 0
            taxa_cancelamento = (stats['canceladas'] / stats['total'] * 100) if stats['total'] > 0 else 0
            
            relatorio.append({
                'periodo': stats['periodo'],
                'total_reservas': stats['total'],
                'reservas_confirmadas': stats['confirmadas'],
                'reservas_canceladas': stats['canceladas'],
                'reservas_pendentes': stats['pendentes'],
                'pessoas_total': stats['pessoas'],
                'ticket_medio': round(ticket_medio, 2),
                'taxa_cancelamento': round(taxa_cancelamento, 2),
            })
        
        # Ordenar por período
        relatorio.sort(key=lambda x: x['periodo'])
        return relatorio
