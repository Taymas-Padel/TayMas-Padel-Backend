from django.urls import path
from . import views

urlpatterns = [
    # Канбан-доска (все стадии сразу)
    path('kanban/', views.leads_kanban, name='leads-kanban'),

    # Статистика воронки
    path('stats/', views.leads_stats, name='leads-stats'),

    # Список лидов + создание
    path('', views.leads_list_create, name='leads-list-create'),

    # Детали / редактирование / удаление лида
    path('<int:pk>/', views.lead_detail, name='lead-detail'),

    # Смена стадии (drag & drop)
    path('<int:pk>/move/', views.lead_move_stage, name='lead-move-stage'),

    # Комментарии (история взаимодействий)
    path('<int:pk>/comments/', views.lead_comments, name='lead-comments'),
    path('<int:pk>/comments/<int:comment_id>/', views.lead_comment_delete, name='lead-comment-delete'),

    # Задачи / напоминания
    path('<int:pk>/tasks/', views.lead_tasks, name='lead-tasks'),
    path('<int:pk>/tasks/<int:task_id>/', views.lead_task_detail, name='lead-task-detail'),
]
