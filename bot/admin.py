from django.contrib import admin
from django.utils.html import format_html
from .models import Task, Category


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "short_description",
        "completed",
        "user",
        "categories_display",
        "created_at_formatted",
        "is_overdue",
    )
    list_filter = ("created_at", "title", "user", "due_date", "completed", "categories")
    search_fields = ("description", "title", "user__username")
    readonly_fields = ("created_at", "id")
    list_per_page = 25

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
    readonly_fields = ("id", "task_count")
