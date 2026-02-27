from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='NewsItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Заголовок')),
                ('content', models.TextField(verbose_name='Текст')),
                ('category', models.CharField(
                    choices=[
                        ('NEWS', 'Новость'),
                        ('EVENT', 'Мероприятие / Турнир'),
                        ('PROMO', 'Акция'),
                        ('ANNOUNCEMENT', 'Объявление'),
                    ],
                    default='NEWS',
                    max_length=20,
                    verbose_name='Категория',
                )),
                ('image_url', models.URLField(blank=True, null=True, verbose_name='Ссылка на картинку')),
                ('is_published', models.BooleanField(default=True, verbose_name='Опубликовано')),
                ('is_pinned', models.BooleanField(default=False, verbose_name='Закреплено')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата публикации')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Новость / Объявление',
                'verbose_name_plural': 'Новости и объявления',
                'ordering': ['-is_pinned', '-created_at'],
            },
        ),
    ]
