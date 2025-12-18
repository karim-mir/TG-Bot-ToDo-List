from Homework_1.src.categorize_transactions import categories
from django.contrib import admin
from django.utils.html import format_html
from .models import Task, Category


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "get_short_description",
        "completed",
        "user",
        "get_categories_display",
        "created_at_formatted",
    )
    list_filter = ("created_at", "title", "user", "due_date", "completed", "categories")
    search_fields = ("description", "title", "user__username")
    readonly_fields = ("created_at", "id")
    list_per_page = 25

    def get_categories_display(self, obj):
        """Отображает категории"""
        categories = obj.categories.all()
        if categories:
            return ", ".join([cat.name for cat in categories])
        return "Без категории"
    get_categories_display.short_description = "Категория"

    def get_short_description(self, obj):
        """Сокращенное описание для списка"""
        if obj.description:
            return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
        return "Без описания"
    get_short_description.short_description = "Описание"

    def created_at_formatted(self, obj):
        """Форматированная дата создания"""
        return obj.created_at.strftime("%d.%m.%Y %H:%M")
    created_at_formatted.short_description = "Создано"


    fieldsets = (
        (
            "Основная информация",
            {"fields": ("title", "description", "completed", "user", "categories")},
        ),
        (
            "Даты",
            {
                "fields": ("created_at", "due_date"),
                "classes": ("collapse",),
            },
        )
    )

    filter_horizontal = ("categories",)

    autocomplete_fields = ["user"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "task_count")
    list_filter = ("user",)
    search_fields = ("name", "user__username")
    readonly_fields = ("id",)

    def task_count(self, obj):
        """Количество задач в категории"""
        return obj.task_set.count()
    task_count.short_description = "Кол-во задач"

    prepopulated_fields = {"name": ("name",)}
