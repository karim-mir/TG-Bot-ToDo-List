from django.db import models
from django.utils import timezone
from datetime import datetime
from django.contrib.auth import get_user_model
import secrets

User = get_user_model()


class Category(models.Model):
    id = models.CharField(max_length=50, primary_key=True, editable=False)
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    @property
    def task_count(self):
        """Количество задач в категории"""
        return self.task_set.count()

    def save(self, *args, **kwargs):
        if not self.id:
            timestap = datetime.now().strftime("%Y%m%d")
            random_part = secrets.token_hex(3).upper()
            self.id = f"CAT-{timestap}-{random_part}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        unique_together = ["name", "user"]


class Task(models.Model):
    id = models.CharField(max_length=50, primary_key=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    completed = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    categories = models.ManyToManyField(Category, blank=True)

    @property
    def short_description(self):
        """Сокращенное описание"""
        if self.description:
            return (self.description[:50] + "...") if len(self.description) > 50 else self.description
        return "Без описания"

    @property
    def created_at_formatted(self):
        """Форматированная дата создания"""
        return self.created_at.strftime("%d.%m.%Y %H:%M")

    @property
    def due_date_formatted(self):
        """Форматированная дата выполнения"""
        if self.due_date:
            return self.due_date.strftime("%d.%m.%Y %H:%M")
        return "Не установлена"

    @property
    def categories_display(self):
        """Отображает категории"""
        categories = self.categories.all()
        if categories:
            return ", ".join([cat.name for cat in categories])
        return "Без категории"

    @property
    def is_overdue(self):
        """Проверка, просрочена ли задача"""
        if self.due_date and not self.completed:
            return self.due_date < timezone.now()
        return False

    @property
    def days_until_due(self):
        """Дней до дедлайна"""
        if self.due_date:
            now = timezone.now()
            if self.due_date < now:
                return f"Просрочено на {(now - self.due_date).days} дн."
            return (self.due_date - now).days
        return None

    def save(self, *args, **kwargs):
        if not self.id:
            timestamp = datetime.now().strftime("%Y%m%d")
            random_part = secrets.token_hex(3).upper()
            self.id = f"TASK-{timestamp}-{random_part}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        indexes = [
            models.Index(fields=["user", "completed"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["created_at"]),
        ]
