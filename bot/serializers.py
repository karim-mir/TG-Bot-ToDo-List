from rest_framework import serializers

from .models import Category, Task


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "user_id", "created_at"]
        read_only_fields = ["created_at"]
        extra_kwargs = {"user_id": {"required": False}}  # user_id не обязателен


class TaskSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Category.objects.all(),
        source="categories",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "user",
            "completed",
            "due_date",
            "categories",
            "category_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"user": {"required": False}}


class TaskListSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "user",
            "completed",
            "due_date",
            "categories",
            "created_at",
        ]


class TaskCreateSerializer(serializers.ModelSerializer):
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Category.objects.all(),
        source="categories",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Task
        fields = ["id", "title", "description", "user", "due_date", "category_ids"]
        read_only_fields = ["id"]  # Убрали 'user' отсюда!
        extra_kwargs = {"user": {"required": False}}  # Оставляем необязательным

    def create(self, validated_data):
        # Извлекаем категории
        categories = validated_data.pop("categories", [])

        # Создаем задачу
        task = Task.objects.create(**validated_data)

        # Добавляем категории
        if categories:
            task.categories.set(categories)

        return task
