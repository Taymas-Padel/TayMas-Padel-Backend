# Generated manually for coach price by player count (1-2 vs 3-4)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='coach_price_1_2',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                verbose_name='Цена тренера за час (1–2 игрока)',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='coach_price_3_4',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                verbose_name='Цена тренера за час (3–4 игрока)',
            ),
        ),
    ]
