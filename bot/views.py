from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Task
from .serializers import (CategorySerializer, TaskCreateSerializer,
                          TaskListSerializer, TaskSerializer)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с категориями"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]  # Изменено: разрешаем доступ всем
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        """Получаем категории, фильтруем по user_id если передан"""
        queryset = super().get_queryset()

        # Получаем user_id из query parameters
        user_id = self.request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Если передан заголовок авторизации или пользователь аутентифицирован
        if self.request.user and self.request.user.is_authenticated:
            if self.request.user.is_staff:
                return queryset
            return queryset.filter(user=self.request.user)

        return queryset  # Для неаутентифицированных возвращаем все

    def perform_create(self, serializer):
        """Просто сохраняем категорию с данными из запроса"""
        serializer.save()

    @action(detail=True, methods=["get"])
    def tasks(self, request, pk=None):
        """Получаем все задачи категории"""
        category = self.get_object()
        tasks = category.task_set.all()

        # Фильтруем по user_id если передан
        user_id = request.query_params.get("user_id")
        if user_id:
            tasks = tasks.filter(user_id=user_id)

        # Если пользователь аутентифицирован и не staff, фильтруем по нему
        if request.user.is_authenticated and not request.user.is_staff:
            tasks = tasks.filter(user=request.user)

        serializer = TaskSerializer(tasks, many=True, context={"request": request})
        return Response(serializer.data)


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с задачами"""

    queryset = Task.objects.all()
    permission_classes = [permissions.AllowAny]  # Изменено: разрешаем доступ всем
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
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
        """Получаем задачи, фильтруем по user_id если передан"""
        queryset = super().get_queryset()

        # Получаем user_id из query parameters
        user_id = self.request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Если передан заголовок авторизации или пользователь аутентифицирован
        if self.request.user and self.request.user.is_authenticated:
            if self.request.user.is_staff:
                return queryset
            return queryset.filter(user=self.request.user)

        return queryset  # Для неаутентифицированных возвращаем все

    def perform_create(self, serializer):
        """Создаем задачу, используя user_id из запроса или текущего пользователя"""
        # Получаем user_id из данных запроса
        user_id = self.request.data.get("user_id")

        if self.request.user and self.request.user.is_authenticated:
            # Если пользователь аутентифицирован, используем его
            serializer.save(user=self.request.user)
        elif user_id:
            # Если передан user_id, используем его
            serializer.save(user_id=user_id)
        else:
            # Иначе сохраняем без пользователя
            serializer.save()

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
