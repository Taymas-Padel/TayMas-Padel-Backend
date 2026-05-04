from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='status',
            field=models.CharField(
                choices=[('sent', 'Отправлено'), ('delivered', 'Доставлено'), ('read', 'Прочитано')],
                default='sent',
                max_length=10,
                verbose_name='Статус',
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='client_message_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=100,
                null=True,
                verbose_name='Клиентский ID',
            ),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(
                fields=['conversation', 'created_at'],
                name='chat_msg_conv_created_idx',
            ),
        ),
        migrations.AddConstraint(
            model_name='message',
            constraint=models.UniqueConstraint(
                condition=models.Q(client_message_id__isnull=False),
                fields=['conversation', 'sender', 'client_message_id'],
                name='unique_client_message_id_per_conv',
            ),
        ),
    ]
