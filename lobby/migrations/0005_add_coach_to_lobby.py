# Generated manually for coach on lobby

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('lobby', '0004_remove_lobby_level_lobby_elo_max_lobby_elo_min_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lobby',
            name='coach',
            field=models.ForeignKey(
                blank=True,
                help_text='При создании брони из лобби тренер будет назначен в бронь и увидит её в расписании.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lobbies_as_coach',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Тренер',
            ),
        ),
    ]
