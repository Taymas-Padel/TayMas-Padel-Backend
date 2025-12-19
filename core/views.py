from rest_framework.generics import ListAPIView
from .models import ClubSetting
from .serializers import ClubSettingSerializer
from rest_framework.permissions import AllowAny

class ClubSettingListView(ListAPIView):
    """
    Отдает список настроек (время работы, правила отмены).
    Доступно всем (даже без регистрации).
    """
    queryset = ClubSetting.objects.all()
    serializer_class = ClubSettingSerializer
    permission_classes = [AllowAny]