from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('loja', '0010_clube_e_combo'),
    ]

    operations = [
        migrations.CreateModel(
            name='InscricaoNewsletter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Inscrição na newsletter',
                'verbose_name_plural': 'Inscrições na newsletter',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='Avaliacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nota', models.PositiveSmallIntegerField()),
                ('comentario', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='avaliacoes', to='loja.produto')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='avaliacoes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Avaliação',
                'verbose_name_plural': 'Avaliações',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.AddConstraint(
            model_name='avaliacao',
            constraint=models.UniqueConstraint(fields=('usuario', 'produto'), name='uniq_avaliacao_usuario_produto'),
        ),
        migrations.AddConstraint(
            model_name='avaliacao',
            constraint=models.CheckConstraint(check=models.Q(('nota__gte', 1), ('nota__lte', 5)), name='avaliacao_nota_1_a_5'),
        ),
    ]
