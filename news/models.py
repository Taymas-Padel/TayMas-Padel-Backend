from django.db import models


class NewsItem(models.Model):
    CATEGORY_CHOICES = [
        ('NEWS', 'Новость'),
        ('EVENT', 'Мероприятие / Турнир'),
        ('PROMO', 'Акция'),
        ('ANNOUNCEMENT', 'Объявление'),
    ]

    title = models.CharField(max_length=200, verbose_name="Заголовок")
    content = models.TextField(verbose_name="Текст")
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='NEWS', verbose_name="Категория"
    )
    image_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на картинку")
    is_published = models.BooleanField(default=True, verbose_name="Опубликовано")
    is_pinned = models.BooleanField(default=False, verbose_name="Закреплено")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата публикации")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Новость / Объявление"
        verbose_name_plural = "Новости и объявления"
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"
