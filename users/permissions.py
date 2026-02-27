from rest_framework.permissions import BasePermission


class IsReceptionist(BasePermission):
    """Ресепшн и ADMIN — доступ к клиентским данным."""
    message = "Доступно только для ресепшн и администраторов."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['ADMIN', 'RECEPTIONIST']


class IsAdminRole(BasePermission):
    """Только ADMIN (не через is_staff, а через кастомную role)."""
    message = "Доступно только для администраторов."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == 'ADMIN'


class IsStaffMember(BasePermission):
    """ADMIN, RECEPTIONIST, COACH_PADEL, COACH_FITNESS — любой сотрудник клуба."""
    message = "Доступно только для сотрудников клуба."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['ADMIN', 'RECEPTIONIST', 'COACH_PADEL', 'COACH_FITNESS']


class IsCoach(BasePermission):
    """Любой тренер (падел или фитнес)"""
    message = "Доступно только для тренеров."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['COACH_PADEL', 'COACH_FITNESS', 'ADMIN']


class IsPadelCoach(BasePermission):
    """Только тренер по паделу"""
    message = "Доступно только для тренеров по паделу."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['COACH_PADEL', 'ADMIN']


class IsFitnessCoach(BasePermission):
    """Только фитнес-тренер"""
    message = "Доступно только для фитнес-тренеров."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['COACH_FITNESS', 'ADMIN']


class IsSuperAdmin(BasePermission):
    """Только супер-админ"""
    message = "Доступно только для администраторов."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == 'ADMIN'


class IsProfileComplete(BasePermission):
    """
    Проверяет что у юзера заполнен профиль (имя + фамилия).
    Если нет — блокируем доступ ко всем эндпоинтам кроме обновления профиля.
    """
    message = "Заполните профиль (имя и фамилию) для продолжения."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True  # Пропускаем — пусть дальше проверяет IsAuthenticated
        return request.user.is_profile_complete