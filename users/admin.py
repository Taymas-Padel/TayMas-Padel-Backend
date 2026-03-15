from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from .models import User


# =============================================
# ФОРМА СОЗДАНИЯ НОВОГО ПОЛЬЗОВАТЕЛЯ
# =============================================

class CustomUserCreationForm(forms.ModelForm):
    """
    Форма создания юзера в админке.
    - Для персонала (ADMIN, RECEPTIONIST): логин + пароль ОБЯЗАТЕЛЬНЫ
    - Для клиентов/тренеров: пароль НЕ нужен (вход по SMS), логин генерируется автоматически
    """
    username = forms.CharField(
        label="Логин (для CRM)",
        required=False,
        help_text="Для входа в CRM. Если пусто — сгенерируется из номера телефона.",
    )
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput,
        required=False,
        help_text="Обязательно для ресепшн и админов. Для клиентов/тренеров — не нужен.",
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput,
        required=False,
    )

    class Meta:
        model = User
        fields = ('phone_number', 'username', 'first_name', 'last_name', 'role')

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        username = cleaned_data.get('username')
        phone = cleaned_data.get('phone_number')

        # Роли, которым нужен пароль для CRM
        staff_roles = [User.Role.SUPER_ADMIN, User.Role.RECEPTIONIST]

        if role in staff_roles:
            if not password1:
                self.add_error('password1', 'Для ресепшн и админов пароль обязателен.')
            if not username and not phone:
                self.add_error('username', 'Укажите логин или номер телефона.')

        if password1 and password1 != password2:
            self.add_error('password2', 'Пароли не совпадают.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        # Генерируем username если не указан
        if not user.username:
            if user.phone_number:
                # Логин = номер телефона (без +)
                user.username = user.phone_number.replace('+', '')
            else:
                # Фоллбек: имя + рандом
                import random
                user.username = f"user_{random.randint(10000, 99999)}"

        # Пароль
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        # Персонал автоматически получает is_staff для доступа к админке и CRM
        staff_roles = [User.Role.SUPER_ADMIN, User.Role.RECEPTIONIST]
        if user.role in staff_roles:
            user.is_staff = True
        if user.role == User.Role.SUPER_ADMIN:
            user.is_superuser = True

        if commit:
            user.save()
        return user


# =============================================
# АДМИНКА ПОЛЬЗОВАТЕЛЕЙ
# =============================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # --- ФОРМА СОЗДАНИЯ ---
    add_form = CustomUserCreationForm

    # --- СПИСОК ---
    list_display = (
        'id', 'get_phone', 'get_login', 'first_name', 'last_name',
        'role', 'is_qr_blocked', 'get_profile_status', 'get_has_password',
    )
    list_display_links = ('id', 'get_phone')
    search_fields = ('phone_number', 'first_name', 'last_name', 'username')
    list_filter = ('role', 'is_qr_blocked', 'is_active', 'is_staff')
    ordering = ('-id',)

    # --- КАСТОМНЫЕ КОЛОНКИ ---
    @admin.display(description='Телефон', ordering='phone_number')
    def get_phone(self, obj):
        return obj.phone_number or '—'

    @admin.display(description='Логин', ordering='username')
    def get_login(self, obj):
        # Показываем логин только если он отличается от телефона
        phone_clean = (obj.phone_number or '').replace('+', '')
        if obj.username and obj.username != obj.phone_number and obj.username != phone_clean:
            return obj.username
        return '—'

    @admin.display(description='Профиль', boolean=True)
    def get_profile_status(self, obj):
        return obj.is_profile_complete

    @admin.display(description='Есть пароль', boolean=True)
    def get_has_password(self, obj):
        return obj.has_usable_password()

    # --- РЕДАКТИРОВАНИЕ СУЩЕСТВУЮЩЕГО ---
    fieldsets = (
        ('Основная информация', {
            'fields': ('phone_number', 'username', 'first_name', 'last_name', 'avatar')
        }),
        ('Роль и параметры', {
            'fields': ('role', 'price_per_hour', 'coach_price_1_2', 'coach_price_3_4', 'rating_elo'),
            'description': 'RECEPTIONIST = ресепшн (вход в CRM по паролю). '
                           'CLIENT/COACH = вход через SMS в приложении. '
                           'Для тренера: price_per_hour — по умолчанию; coach_price_1_2 / coach_price_3_4 — тариф за час (1–2 и 3–4 игрока).',
        }),
        ('Безопасность', {
            'fields': ('is_qr_blocked', 'last_device_id', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Пароль', {
            'classes': ('collapse',),
            'fields': ('password',),
            'description': 'Для смены пароля используйте ссылку ниже.',
        }),
    )

    # --- СОЗДАНИЕ НОВОГО ---
    add_fieldsets = (
        ('Контакт', {
            'fields': ('phone_number', 'first_name', 'last_name'),
            'description': 'Номер телефона обязателен для всех.',
        }),
        ('Доступ', {
            'fields': ('role', 'username', 'password1', 'password2'),
            'description': '<b>Ресепшн / Админ</b>: укажите логин и пароль для входа в CRM.<br>'
                           '<b>Клиент / Тренер</b>: пароль не нужен (вход по SMS). '
                           'Логин создастся автоматически из номера.',
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return ()