from rest_framework import serializers
from django.utils import timezone
from .models import Task, Category
from django.contrib.auth import get_user_model

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категорий"""
    task_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "user", "task_count"]
        read_only_fields = ["id", "task_count"]


class UserSimpleSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя"""
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class TaskSerializer(serializers.ModelSerializer):

    short_description = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True)
    categories_display = serializers.CharField(read_only=True)
    is_overdue = serializers.CharField(read_only=True)
    days_until_due = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)

    user = UserSimpleSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryse=User.objects.all(),
        source="user",
        write_only=True,
        required=False,
        help_text="ID пользователя"
    )

    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryse=Category.objects.all(),
        source="categories",
        write_only=True,
        required=False,
        help_text="Список ID категорий"
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "short_description",
            "completed",
            "user",
            "user_id",
            "categories",
            "category_ids",
            "categories_display",
            "created_at",
            "created_at_formatted",
            "due_date",
            "days_until_due",
            "is_overdue",
            "status_display",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "short_description",
            "created_at_formatted",
            "categories_display",
            "days_until_due",
            "is_overdue",
            "status_display",
        ]
        extra_kwargs = {
            "description": {"required": True, "allow_blank": True},
            "due_date": {"required": True},
        }

        def validate_title(self, value):
            """Валидация заголовка"""
            value = value.strip()
            if len(value) < 3:
                raise serializers.ValidationError("Заголовок должен содержать минимум 3 символа")
            if len(value) > 200:
                raise serializers.ValidationError("Заголовок не должен превышать 200 символов")
            return value

        def validate_due_date(self, value):
            """Валидация даты выполнения"""
            if value < timezone.now():
                raise serializers.ValidationError("Дата выполнения не может быть в прошлом")
            return value

        def create(self, validated_data):
            """Создание задачи с автоматическим назначением пользователя"""
            if "user" not in validated_data and self.context.get("request"):
                validated_data["user"] = self.context["request"].user

            task = Task.objects.create(**validated_data)
            return task

        def update(self, instance, validated_data):
            """Обновление задачи"""
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.save()
            return instance


class TaskListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка задач"""
    user = serializers.StringRelatedField()
    categories = serializers.StringRelatedField(many=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "short_description",
            "completed",
            "user",
            "categories",
            "created_at_formatted",
            "due_date",
            "is_overdue",
        ]
        read_only_fields = fields


class TaskCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания задачи"""
    class Meta:
        model = Task
        fields = [
            'title',
            'description',
            'due_date',
            'category_ids'
        ]
        extra_kwargs = {
            "due_date": {"required": True},
        }
