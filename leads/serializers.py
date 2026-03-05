from rest_framework import serializers
from .models import Lead, LeadComment, LeadTask

ASSIGNABLE_ROLES = ['ADMIN', 'RECEPTIONIST', 'SALES_MANAGER']


class LeadTaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    due_datetime_formatted = serializers.SerializerMethodField()

    class Meta:
        model = LeadTask
        fields = [
            'id', 'title', 'due_datetime', 'due_datetime_formatted',
            'assigned_to', 'assigned_to_name', 'is_done', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip() or obj.assigned_to.username
        return None

    def get_due_datetime_formatted(self, obj):
        return obj.due_datetime.strftime('%d.%m.%Y %H:%M')


class LeadCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = LeadComment
        fields = ['id', 'text', 'author', 'author_name', 'created_at', 'created_at_formatted']
        read_only_fields = ['id', 'author', 'created_at']

    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.username

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')


class LeadListSerializer(serializers.ModelSerializer):
    """Лёгкий сериализатор для канбан-доски (без полных данных комментариев)."""
    assigned_to_name = serializers.SerializerMethodField()
    source_label = serializers.SerializerMethodField()
    stage_label = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()
    last_contact_formatted = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    tasks_count = serializers.SerializerMethodField()
    open_tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id', 'name', 'phone', 'email',
            'source', 'source_label',
            'stage', 'stage_label',
            'assigned_to', 'assigned_to_name',
            'last_contact', 'last_contact_formatted',
            'created_at', 'created_at_formatted',
            'comments_count', 'tasks_count', 'open_tasks_count',
        ]

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip() or obj.assigned_to.username
        return None

    def get_source_label(self, obj):
        return obj.get_source_display()

    def get_stage_label(self, obj):
        return obj.get_stage_display()

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime('%d.%m.%Y')

    def get_last_contact_formatted(self, obj):
        if obj.last_contact:
            return obj.last_contact.strftime('%d.%m.%Y %H:%M')
        return None

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_tasks_count(self, obj):
        return obj.tasks.count()

    def get_open_tasks_count(self, obj):
        return obj.tasks.filter(is_done=False).count()


class LeadDetailSerializer(serializers.ModelSerializer):
    """Полный сериализатор с историей взаимодействий и задачами."""
    assigned_to_name = serializers.SerializerMethodField()
    source_label = serializers.SerializerMethodField()
    stage_label = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()
    last_contact_formatted = serializers.SerializerMethodField()
    comments = LeadCommentSerializer(many=True, read_only=True)
    tasks = LeadTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'name', 'phone', 'email',
            'source', 'source_label',
            'stage', 'stage_label',
            'notes',
            'assigned_to', 'assigned_to_name',
            'last_contact', 'last_contact_formatted',
            'created_at', 'created_at_formatted',
            'comments', 'tasks',
        ]
        read_only_fields = ['id', 'created_at']

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip() or obj.assigned_to.username
        return None

    def get_source_label(self, obj):
        return obj.get_source_display()

    def get_stage_label(self, obj):
        return obj.get_stage_display()

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')

    def get_last_contact_formatted(self, obj):
        if obj.last_contact:
            return obj.last_contact.strftime('%d.%m.%Y %H:%M')
        return None


class LeadCreateUpdateSerializer(serializers.ModelSerializer):
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=None,
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Lead
        fields = [
            'name', 'phone', 'email', 'source', 'stage',
            'notes', 'assigned_to', 'last_contact',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()
        if self.fields['assigned_to'].queryset is None:
            self.fields['assigned_to'].queryset = UserModel.objects.filter(
                role__in=ASSIGNABLE_ROLES
            )
