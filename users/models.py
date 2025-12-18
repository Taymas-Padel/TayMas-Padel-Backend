from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'ADMIN', _('Super Admin')
        MANAGER = 'MANAGER', _('Manager')
        COACH_PADEL = 'COACH_PADEL', _('Padel Coach')
        COACH_FITNESS = 'COACH_FITNESS', _('Fitness Coach')
        CLIENT = 'CLIENT', _('Client')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
        verbose_name=_("Role")
    )
    
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # --- ВОТ ЭТОЙ СТРОКИ НЕ ХВАТАЛО ---
    rating_elo = models.IntegerField(default=1200, verbose_name=_("ELO Rating")) 

    def __str__(self):
        return self.username