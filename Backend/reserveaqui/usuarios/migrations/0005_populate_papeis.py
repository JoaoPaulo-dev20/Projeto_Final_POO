from django.db import migrations


def criar_papeis(apps, schema_editor):
    """Cria os papéis padrão do sistema"""
    Papel = apps.get_model('usuarios', 'Papel')
    
    papeis_data = [
        ('admin_sistema', 'Admin do Sistema'),
        ('admin_secundario', 'Admin Secundário'),
        ('funcionario', 'Funcionário'),
        ('cliente', 'Cliente'),
    ]
    
    for tipo, descricao in papeis_data:
        Papel.objects.get_or_create(
            tipo=tipo,
            defaults={'descricao': ''}
        )


def remover_papeis(apps, schema_editor):
    """Remove os papéis se precisar fazer rollback"""
    Papel = apps.get_model('usuarios', 'Papel')
    Papel.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_usuario_precisa_trocar_senha'),
    ]

    operations = [
        migrations.RunPython(criar_papeis, remover_papeis),
    ]
