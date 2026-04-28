from django.contrib import admin
from .models import Conversation, Message

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    # Запрещаем удаление и добавление сообщений через инлайн для безопасности истории
    can_delete = False 
    readonly_fields = ('sender', 'text', 'is_read', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        # Ограничиваем вывод последними 50 сообщениями, чтобы админка не зависла
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')[:50]

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user1', 'user2', 'updated_at')
    search_fields = ('user1__first_name', 'user2__first_name', 'user1__phone_number', 'user2__phone_number')
    inlines = [MessageInline]
    # Заменяем выпадающий список на окно поиска по ID
    raw_id_fields = ('user1', 'user2') 

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'short_text', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('text',)
    # То же самое для сообщений
    raw_id_fields = ('conversation', 'sender')

    def short_text(self, obj):
        return obj.text[:60]
    short_text.short_description = 'Текст'