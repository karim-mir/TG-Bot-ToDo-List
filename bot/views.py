from wsgiref.simple_server import server_version

from rest_framework import viewsets, permissions, status
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Task, Category
from .serializers import TaskSerializer, TaskListSerializer, TaskCreateSerializer, CategorySerializer

class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с категориями"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        """Пользователи могут видеть только свои категории"""
        queryset = super().get_queryset()

        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Автоматически назначает текущего пользователя"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get"])
    def tasks(self, request, pk=None):
        """Получает все задачи категории"""
        category = self.get_object()
        tasks = category.task_set.all()

        if not request.user.is_staff:
            tasks = tasks.filter(user=request.user)
        serializer = TaskSerializer(tasks, many=True, context={"request": request})
        return Response(serializer.data)


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с задачами"""
    queryset = Task.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ["completed", "categories", "user"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "due_date", "title"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия"""
        if self.action == "list":
            return TaskListSerializer
        elif self.action == "create":
            return TaskCreateSerializer
        return TaskSerializer

    def get_queryset(self):
        """Пользователи могут видеть только свои задачи"""
        queryset = super().get_queryset()

        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Автоматически назначает текущего пользователя"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Отметить задачу как выполненную"""
        task = self.get_object()
        task.completed = True
        task.save()
        return Response({"status": "task_completed"})

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        """Отметить задачу как невыполненную"""
        task = self.get_object()
        task.completed = False
        task.save()
        return Response({"status": "task reopened"})

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        """Получить просроченные задачи"""
        queryset = self.get_queryset().filter(is_overdue=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
