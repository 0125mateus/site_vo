from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('loja', '0007_midia_trailer'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgressoReproducao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('segundos', models.PositiveIntegerField(default=0)),
                ('duracao_segundos', models.PositiveIntegerField(blank=True, null=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('item_pedido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progressos', to='loja.itempedido')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progressos_reproducao', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Progresso de reprodução',
                'verbose_name_plural': 'Progressos de reprodução',
            },
        ),
        migrations.AddConstraint(
            model_name='progressoreproducao',
            constraint=models.UniqueConstraint(fields=('usuario', 'item_pedido'), name='uniq_progresso_usuario_item'),
        ),
    ]
