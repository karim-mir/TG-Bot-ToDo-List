import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Расписание только для Telegram уведомлений
app.conf.beat_schedule = {
    "check-overdue-tasks-hourly": {
        "task": "bot.tasks.check_overdue_tasks",
        "schedule": crontab(minute=0, hour="*"),  # Каждый час
    },
    "send-daily-reminders": {
        "task": "bot.tasks.send_daily_reminders",
        "schedule": crontab(hour=9, minute=0),  # Каждый день в 9:00
    },
}
