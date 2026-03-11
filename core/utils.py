"""
Вспомогательные функции для настроек клуба (график работы).
CLOSE_TIME = "00:00" трактуется как «закрытие в полночь» (конец рабочего дня).
"""
from .models import ClubSetting


def get_club_work_hours():
    """
    Возвращает (open_hour, close_hour, close_at_midnight).
    close_at_midnight = True, если в настройках указано 00:00 (закрытие в полночь).
    """
    open_s = ClubSetting.objects.filter(key='OPEN_TIME').first()
    close_s = ClubSetting.objects.filter(key='CLOSE_TIME').first()
    open_h = int(open_s.value.split(':')[0]) if open_s else 7
    close_h = int(close_s.value.split(':')[0]) if close_s else 23
    close_at_midnight = (close_h == 0)
    return open_h, close_h, close_at_midnight


def work_hours_display_string(open_h, close_h, close_at_midnight):
    """Строка для отображения: «7:00 – 24:00» или «7:00 – 23:00»."""
    close_label = "24:00" if close_at_midnight else f"{close_h}:00"
    return f"{open_h}:00 – {close_label}"
