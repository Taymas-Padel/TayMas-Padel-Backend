# Отмена лобби: возврат денег и часов. FK абонемента + часы у участника, статус CANCELED у лобби.

from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('memberships', '0001_initial'),
        ('lobby', '0006_lobby_wants_coach'),
    ]

    operations = [
        migrations.AddField(
            model_name='lobbyparticipant',
            name='booking_membership',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lobby_participant_uses',
                to='memberships.usermembership',
                verbose_name='Абонемент на бронь',
            ),
        ),
        migrations.AddField(
            model_name='lobbyparticipant',
            name='hours_used',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=6,
                null=True,
                verbose_name='Списано часов с абонемента',
            ),
        ),
        migrations.AlterField(
            model_name='lobby',
            name='status',
            field=models.CharField(
                choices=[
                    ('OPEN', 'Ищем игроков'),
                    ('WAITING', 'Частично заполнено'),
                    ('NEGOTIATING', 'Согласование времени/корта'),
                    ('READY', 'Время согласовано — ждём бронь'),
                    ('BOOKED', 'Бронь создана — ждём оплату'),
                    ('PAID', 'Все оплатили — бронь подтверждена'),
                    ('CANCELED', 'Бронь отменена'),
                    ('CLOSED', 'Закрыто'),
                ],
                default='OPEN',
                max_length=12,
                verbose_name='Статус',
            ),
        ),
    ]
