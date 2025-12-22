from django.contrib import admin

from .models import Category, Task


class CategoryAdmin(admin.ModelAdmin):
    """Админ-панель для категорий"""

    list_display = ["id", "name", "user", "created_at"]
    list_filter = ["user", "created_at"]
    search_fields = ["name", "user__username"]
    readonly_fields = ["created_at"]
    raw_id_fields = ["user"]


class TaskAdmin(admin.ModelAdmin):
    """Админ-панель для задач"""

    list_display = ["id", "title", "user", "completed", "due_date", "created_at"]
    list_filter = ["completed", "user", "categories", "created_at", "due_date"]
    search_fields = ["title", "description", "user__username"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["user"]
    filter_horizontal = ["categories"]


# Регистрация моделей
admin.site.register(Task, TaskAdmin)
admin.site.register(Category, CategoryAdmin)
