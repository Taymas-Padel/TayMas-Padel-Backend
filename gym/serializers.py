from rest_framework import serializers

class ScanQRSerializer(serializers.Serializer):
    qr_content = serializers.CharField(help_text="Зашифрованная строка QR")
    
    # 👇 Добавляем выбор локации
    LOCATION_CHOICES = [
        ('GYM', 'Турникет Зала'),
        ('PADEL', 'Ресепшен Падела'),
        ('ALL', 'Общий вход (если есть)'),
    ]
    location = serializers.ChoiceField(choices=LOCATION_CHOICES, default='ALL')