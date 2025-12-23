from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """Профиль пользователя для Telegram"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="telegram_profile"
    )
    telegram_id = models.BigIntegerField(unique=True, verbose_name="ID Telegram")
    username = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Имя пользователя"
    )
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username or self.telegram_id} (User: {self.user.username})"

    class Meta:
        verbose_name = "Профиль Telegram"
        verbose_name_plural = "Профили Telegram"


class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название категории")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="categories",
        verbose_name="Пользователь",
        null=True,  # Разрешаем null для тестов
        blank=True,  # Разрешаем пустое значение
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"{self.name} (User: {self.user_id})"

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["-created_at"]


class Task(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название задачи")
    description = models.TextField(blank=True, verbose_name="Описание")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Пользователь",
        null=True,  # Разрешаем null для тестов
        blank=True,  # Разрешаем пустое значение
    )
    completed = models.BooleanField(default=False, verbose_name="Выполнено")
    due_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Срок выполнения"
    )
    categories = models.ManyToManyField(Category, related_name="tasks", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return f"{self.title} (User: {self.user_id})"

    @property
    def is_overdue(self):
        """Проверка, просрочена ли задача"""
        if self.due_date and not self.completed:
            from django.utils import timezone

            return self.due_date < timezone.now()
        return False

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["-created_at"]
