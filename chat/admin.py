from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'text', 'is_read', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user1', 'user2', 'updated_at')
    search_fields = ('user1__first_name', 'user2__first_name', 'user1__phone_number', 'user2__phone_number')
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'short_text', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('text',)

    def short_text(self, obj):
        return obj.text[:60]
    short_text.short_description = 'Текст'
