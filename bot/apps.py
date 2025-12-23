from django.apps import AppConfig


class BotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bot"
    verbose_name = "Telegram Bot"

    def ready(self):
        """Вызывается при запуске Django"""
