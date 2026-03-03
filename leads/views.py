from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone

from users.permissions import IsReceptionist
from .models import Lead, LeadComment, LeadTask
from .serializers import (
    LeadListSerializer,
    LeadDetailSerializer,
    LeadCreateUpdateSerializer,
    LeadCommentSerializer,
    LeadTaskSerializer,
)


# =============================================
# 1. СПИСОК ЛИДОВ + СОЗДАНИЕ
# =============================================

@api_view(['GET', 'POST'])
@permission_classes([IsReceptionist])
def leads_list_create(request):
    """
    GET  /api/leads/?stage=NEW&assigned_to=me&search=Азамат
    POST /api/leads/
    """
    if request.method == 'GET':
        qs = Lead.objects.select_related('assigned_to').prefetch_related('comments', 'tasks')

        stage = request.query_params.get('stage')
        if stage:
            qs = qs.filter(stage=stage)

        assigned_to = request.query_params.get('assigned_to')
        if assigned_to == 'me':
            qs = qs.filter(assigned_to=request.user)
        elif assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(phone__icontains=search)

        serializer = LeadListSerializer(qs, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = LeadCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            lead = serializer.save()
            return Response(LeadDetailSerializer(lead).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =============================================
# 2. КАНБАН — ВСЕ СТАДИИ СРАЗУ
# =============================================

@api_view(['GET'])
@permission_classes([IsReceptionist])
def leads_kanban(request):
    """
    GET /api/leads/kanban/
    Возвращает лиды сгруппированными по стадиям.
    Используется для отрисовки канбан-доски на фронте.
    """
    assigned_to = request.query_params.get('assigned_to')
    search = request.query_params.get('search')

    qs = Lead.objects.select_related('assigned_to').prefetch_related('comments', 'tasks')

    if assigned_to == 'me':
        qs = qs.filter(assigned_to=request.user)
    elif assigned_to:
        qs = qs.filter(assigned_to_id=assigned_to)

    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(phone__icontains=search)

    result = []
    for stage_value, stage_label in Lead.Stage.choices:
        stage_leads = [l for l in qs if l.stage == stage_value]
        result.append({
            'stage': stage_value,
            'label': stage_label,
            'count': len(stage_leads),
            'leads': LeadListSerializer(stage_leads, many=True).data,
        })

    return Response(result)


# =============================================
# 3. ДЕТАЛИ / ОБНОВЛЕНИЕ / УДАЛЕНИЕ ЛИДА
# =============================================

@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsReceptionist])
def lead_detail(request, pk):
    """
    GET    /api/leads/{id}/
    PATCH  /api/leads/{id}/
    DELETE /api/leads/{id}/
    """
    lead = get_object_or_404(Lead, pk=pk)

    if request.method == 'GET':
        return Response(LeadDetailSerializer(lead).data)

    elif request.method == 'PATCH':
        serializer = LeadCreateUpdateSerializer(lead, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(LeadDetailSerializer(lead).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        lead.delete()
        return Response({'status': 'Лид удалён.'}, status=status.HTTP_204_NO_CONTENT)


# =============================================
# 4. СМЕНА СТАДИИ (drag & drop)
# =============================================

@api_view(['POST'])
@permission_classes([IsReceptionist])
def lead_move_stage(request, pk):
    """
    POST /api/leads/{id}/move/
    body: { "stage": "NEGOTIATION" }
    Используется при перетаскивании карточки между колонками.
    """
    lead = get_object_or_404(Lead, pk=pk)
    new_stage = request.data.get('stage')

    valid_stages = [s[0] for s in Lead.Stage.choices]
    if not new_stage or new_stage not in valid_stages:
        return Response(
            {'error': f'Укажите stage. Допустимые: {valid_stages}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    lead.stage = new_stage
    lead.last_contact = timezone.now()
    lead.save(update_fields=['stage', 'last_contact', 'updated_at'])

    return Response({
        'status': 'ok',
        'id': lead.id,
        'stage': lead.stage,
        'stage_label': lead.get_stage_display(),
        'last_contact': lead.last_contact,
    })


# =============================================
# 5. КОММЕНТАРИИ (история взаимодействий)
# =============================================

@api_view(['GET', 'POST'])
@permission_classes([IsReceptionist])
def lead_comments(request, pk):
    """
    GET  /api/leads/{id}/comments/
    POST /api/leads/{id}/comments/    body: { "text": "Клиент перезвонит в пятницу" }
    """
    lead = get_object_or_404(Lead, pk=pk)

    if request.method == 'GET':
        comments = lead.comments.select_related('author').all()
        return Response(LeadCommentSerializer(comments, many=True).data)

    elif request.method == 'POST':
        text = request.data.get('text', '').strip()
        if not text:
            return Response({'error': 'Текст комментария обязателен.'}, status=status.HTTP_400_BAD_REQUEST)

        comment = LeadComment.objects.create(lead=lead, author=request.user, text=text)
        lead.last_contact = timezone.now()
        lead.save(update_fields=['last_contact', 'updated_at'])

        return Response(LeadCommentSerializer(comment).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsReceptionist])
def lead_comment_delete(request, pk, comment_id):
    """
    DELETE /api/leads/{id}/comments/{comment_id}/
    Удалить можно только свой комментарий (или ADMIN — любой).
    """
    comment = get_object_or_404(LeadComment, pk=comment_id, lead_id=pk)

    if comment.author != request.user and request.user.role != 'ADMIN':
        return Response({'error': 'Нельзя удалять чужие комментарии.'}, status=status.HTTP_403_FORBIDDEN)

    comment.delete()
    return Response({'status': 'Комментарий удалён.'}, status=status.HTTP_204_NO_CONTENT)


# =============================================
# 6. ЗАДАЧИ / НАПОМИНАНИЯ
# =============================================

@api_view(['GET', 'POST'])
@permission_classes([IsReceptionist])
def lead_tasks(request, pk):
    """
    GET  /api/leads/{id}/tasks/
    POST /api/leads/{id}/tasks/
    body: { "title": "Перезвонить", "due_datetime": "2026-03-28T14:00:00Z", "assigned_to": 2 }
    """
    lead = get_object_or_404(Lead, pk=pk)

    if request.method == 'GET':
        tasks = lead.tasks.select_related('assigned_to').all()
        return Response(LeadTaskSerializer(tasks, many=True).data)

    elif request.method == 'POST':
        serializer = LeadTaskSerializer(data=request.data)
        if serializer.is_valid():
            task = serializer.save(lead=lead)
            return Response(LeadTaskSerializer(task).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsReceptionist])
def lead_task_detail(request, pk, task_id):
    """
    PATCH  /api/leads/{id}/tasks/{task_id}/
    DELETE /api/leads/{id}/tasks/{task_id}/
    Для отметки выполненной задачи: PATCH body: { "is_done": true }
    """
    task = get_object_or_404(LeadTask, pk=task_id, lead_id=pk)

    if request.method == 'PATCH':
        serializer = LeadTaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(LeadTaskSerializer(task).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        task.delete()
        return Response({'status': 'Задача удалена.'}, status=status.HTTP_204_NO_CONTENT)


# =============================================
# 7. СТАТИСТИКА ВОРОНКИ
# =============================================

@api_view(['GET'])
@permission_classes([IsReceptionist])
def leads_stats(request):
    """
    GET /api/leads/stats/
    Статистика по воронке: количество лидов на каждой стадии, конверсии.
    """
    total = Lead.objects.count()
    stats = []

    for stage_value, stage_label in Lead.Stage.choices:
        count = Lead.objects.filter(stage=stage_value).count()
        stats.append({
            'stage': stage_value,
            'label': stage_label,
            'count': count,
            'percent': round(count / total * 100, 1) if total > 0 else 0,
        })

    sold_count = Lead.objects.filter(stage=Lead.Stage.SOLD).count()

    return Response({
        'total': total,
        'stages': stats,
        'conversion_rate': round(sold_count / total * 100, 1) if total > 0 else 0,
        'sold_count': sold_count,
    })
