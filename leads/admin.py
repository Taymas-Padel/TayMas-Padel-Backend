from django.contrib import admin
from .models import Lead, LeadComment, LeadTask


class LeadCommentInline(admin.TabularInline):
    model = LeadComment
    extra = 0
    readonly_fields = ['author', 'created_at']


class LeadTaskInline(admin.TabularInline):
    model = LeadTask
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'stage', 'source', 'assigned_to', 'last_contact', 'created_at']
    list_filter = ['stage', 'source', 'assigned_to']
    search_fields = ['name', 'phone', 'email']
    list_editable = ['stage']
    inlines = [LeadCommentInline, LeadTaskInline]
    ordering = ['-created_at']


@admin.register(LeadComment)
class LeadCommentAdmin(admin.ModelAdmin):
    list_display = ['lead', 'author', 'text', 'created_at']
    list_filter = ['author']
    search_fields = ['text', 'lead__name']


@admin.register(LeadTask)
class LeadTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'lead', 'assigned_to', 'due_datetime', 'is_done']
    list_filter = ['is_done', 'assigned_to']
    search_fields = ['title', 'lead__name']
    list_editable = ['is_done']
