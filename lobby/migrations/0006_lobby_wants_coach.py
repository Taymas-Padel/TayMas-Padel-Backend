# Generated manually for wants_coach

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lobby', '0005_add_coach_to_lobby'),
    ]

    operations = [
        migrations.AddField(
            model_name='lobby',
            name='wants_coach',
            field=models.BooleanField(default=False, verbose_name='Планируем с тренером'),
        ),
    ]
