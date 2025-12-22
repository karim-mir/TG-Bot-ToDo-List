import asyncio
import logging
import os
from collections import defaultdict
from datetime import timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Task

logger = logging.getLogger(__name__)
User = get_user_model()

# Получаем токен бота из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def send_telegram_message_async(
    chat_id: int, message: str, parse_mode: str = "HTML"
):
    """Асинхронная отправка сообщения в Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Не удалось отправить сообщение: токен бота не установлен")
        return False

    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode)
        await bot.session.close()
        return True
    except TelegramBadRequest as e:
        logger.error(f"Ошибка Telegram API: {e}")
    except TelegramForbiddenError:
        logger.warning(f"Пользователь {chat_id} заблокировал бота")
    except Exception as e:
        logger.error(f"Ошибка отправки в Telegram: {e}")
    return False


def send_telegram_message_sync(chat_id: int, message: str, parse_mode: str = "HTML"):
    """Синхронная обертка для отправки в Telegram (для использования в Celery)"""
    if not chat_id:
        logger.warning("Не указан chat_id для отправки сообщения")
        return False

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            send_telegram_message_async(chat_id, message, parse_mode)
        )
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Ошибка в синхронной отправке Telegram: {e}")
        return False


def get_user_telegram_id(user):
    """Безопасное получение telegram_id из профиля пользователя"""
    if not hasattr(user, "profile"):
        return None
    return user.profile.telegram_id if user.profile.telegram_id else None


@shared_task
def check_overdue_tasks():
    """Проверка просроченных задач с отправкой уведомлений в Telegram"""
    now = timezone.now()

    # Находим задачи, которые просрочены и не выполнены
    overdue_tasks = (
        Task.objects.filter(due_date__lte=now, completed=False)
        .select_related("user", "user__profile")
        .prefetch_related("categories")
    )

    task_count = overdue_tasks.count()

    if task_count == 0:
        logger.info("✅ Просроченных задач не найдено")
        return "✅ Просроченных задач не найдено"

    logger.info(f"🔍 Найдено {task_count} просроченных задач")

    # Отправляем уведомления для каждой задачи
    notified_tasks = 0
    for task in overdue_tasks:
        telegram_id = get_user_telegram_id(task.user)

        if telegram_id:
            send_telegram_notification.delay(task.id)
            notified_tasks += 1
        else:
            logger.warning(f"⚠️ У пользователя {task.user.username} нет telegram_id")

    return f"📨 Уведомления отправлены для {notified_tasks} из {task_count} задач"


@shared_task
def send_telegram_notification(task_id):
    """Отправка уведомления о просроченной задаче в Telegram"""
    try:
        task = (
            Task.objects.select_related("user", "user__profile")
            .prefetch_related("categories")
            .get(id=task_id)
        )

        telegram_id = get_user_telegram_id(task.user)

        if not telegram_id:
            logger.warning(
                f"⚠️ Не удалось отправить уведомление: у пользователя {task.user.username} нет telegram_id"
            )
            return "❌ У пользователя нет telegram_id"

        # Проверяем, включены ли уведомления в профиле
        if hasattr(task.user, "profile") and not task.user.profile.notification_enabled:
            logger.info(
                f"🔕 Уведомления отключены для пользователя {task.user.username}"
            )
            return "🔕 Уведомления отключены"

        # Сколько дней просрочено
        days_overdue = (timezone.now() - task.due_date).days

        # Форматируем категории
        categories_text = ""
        if task.categories.exists():
            categories_list = " • ".join([cat.name for cat in task.categories.all()])
            categories_text = f"\n🏷️ <b>Категории:</b> {categories_list}"

        # Форматируем сообщение
        overdue_indicator = (
            "⏰" if days_overdue <= 1 else "🚨" if days_overdue <= 3 else "💀"
        )

        message = f"""
{overdue_indicator} <b>ЗАДАЧА ПРОСРОЧЕНА!</b>

📌 <b>{task.title}</b>
📅 <b>Срок был:</b> {task.due_date.strftime('%d.%m.%Y в %H:%M')}
⏳ <b>Просрочено:</b> {days_overdue} дней
📝 <b>Описание:</b> {task.description or 'Нет описания'}
{categories_text}

🆔 <b>ID задачи:</b> <code>{task.id}</code>
📋 <b>Дата создания:</b> {task.created_at.strftime('%d.%m.%Y')}

<i>Выполните задачу или используйте команду /edit чтобы изменить срок</i>
"""

        # Отправляем сообщение
        success = send_telegram_message_sync(telegram_id, message)

        if success:
            logger.info(f"✅ Уведомление отправлено для задачи: {task.title}")
            return "✅ Уведомление отправлено"
        else:
            logger.error(
                f"❌ Не удалось отправить уведомление для задачи: {task.title}"
            )
            return "❌ Не удалось отправить уведомление"

    except Task.DoesNotExist:
        logger.error(f"❌ Задача {task_id} не найдена")
        return "❌ Задача не найдена"
    except Exception as e:
        logger.error(f"❌ Ошибка в send_telegram_notification: {e}")
        return f"❌ Ошибка: {e}"


@shared_task
def send_daily_reminders():
    """Ежедневные напоминания о задачах на сегодня через Telegram"""
    now = timezone.now()

    # Сегодня (с 00:00 до 23:59)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Завтра (для предупреждений)
    tomorrow_start = today_end
    tomorrow_end = tomorrow_start + timedelta(days=1)

    logger.info("📅 Отправка ежедневных напоминаний...")

    # Находим задачи на сегодня и завтра
    today_tasks = (
        Task.objects.filter(due_date__range=[today_start, today_end], completed=False)
        .select_related("user", "user__profile")
        .prefetch_related("categories")
    )

    tomorrow_tasks = (
        Task.objects.filter(
            due_date__range=[tomorrow_start, tomorrow_end], completed=False
        )
        .select_related("user", "user__profile")
        .prefetch_related("categories")
    )

    # Группируем задачи по пользователям
    user_today_tasks = defaultdict(list)
    user_tomorrow_tasks = defaultdict(list)

    for task in today_tasks:
        user_today_tasks[task.user].append(task)

    for task in tomorrow_tasks:
        user_tomorrow_tasks[task.user].append(task)

    # Отправляем напоминания
    all_users = set(list(user_today_tasks.keys()) + list(user_tomorrow_tasks.keys()))

    if not all_users:
        logger.info("📭 Нет пользователей для отправки напоминаний")
        return "📭 Нет пользователей для отправки напоминаний"

    for user in all_users:
        telegram_id = get_user_telegram_id(user)

        if not telegram_id:
            continue

        # Проверяем, включены ли уведомления
        if hasattr(user, "profile") and not user.profile.notification_enabled:
            continue

        tasks_today = user_today_tasks.get(user, [])
        tasks_tomorrow = user_tomorrow_tasks.get(user, [])

        # Отправляем напоминание
        send_user_daily_reminder.delay(
            user.id,
            [t.id for t in tasks_today],
            [t.id for t in tasks_tomorrow] if tasks_tomorrow else None,
        )

    logger.info(f"📤 Напоминания запланированы для {len(all_users)} пользователей")
    return f"📤 Напоминания запланированы для {len(all_users)} пользователей"


@shared_task
def send_user_daily_reminder(user_id, today_task_ids, tomorrow_task_ids=None):
    """Отправка персонализированного ежедневного напоминания"""
    try:
        user = User.objects.select_related("profile").get(id=user_id)

        telegram_id = get_user_telegram_id(user)

        if not telegram_id:
            return "❌ У пользователя нет telegram_id"

        # Проверяем, включены ли уведомления
        if hasattr(user, "profile") and not user.profile.notification_enabled:
            return "🔕 Уведомления отключены"

        today_tasks = Task.objects.filter(id__in=today_task_ids).prefetch_related(
            "categories"
        )
        tomorrow_tasks = (
            Task.objects.filter(id__in=tomorrow_task_ids).prefetch_related("categories")
            if tomorrow_task_ids
            else []
        )

        # Получаем время напоминания из профиля
        reminder_time = "09:00"
        if hasattr(user, "profile") and user.profile.daily_reminder_time:
            reminder_time = user.profile.daily_reminder_time.strftime("%H:%M")

        # Формируем персонализированное сообщение
        message_parts = []

        # Приветствие
        greeting_name = (
            user.profile.telegram_first_name
            if hasattr(user, "profile") and user.profile.telegram_first_name
            else user.username
        )
        message_parts.append(f"👋 <b>Доброе утро, {greeting_name}!</b>")
        message_parts.append(f"⏰ <i>Ежедневное напоминание ({reminder_time})</i>\n")

        # Задачи на сегодня
        if today_tasks.exists():
            message_parts.append(f"🎯 <b>Задачи на СЕГОДНЯ ({len(today_tasks)}):</b>")
            for i, task in enumerate(today_tasks, 1):
                time_str = (
                    task.due_date.strftime("%H:%M") if task.due_date else "до конца дня"
                )
                categories = (
                    f" ({task.categories_display})" if task.categories.exists() else ""
                )
                message_parts.append(
                    f"{i}. <b>{task.title}</b>{categories} • ⏰ {time_str}"
                )
        else:
            message_parts.append("🎉 <b>На сегодня задач нет!</b>")

        # Задачи на завтра
        if tomorrow_tasks.exists():
            message_parts.append(
                f"\n🔜 <b>Задачи на ЗАВТРА ({len(tomorrow_tasks)}):</b>"
            )
            for i, task in enumerate(tomorrow_tasks, 1):
                time_str = (
                    task.due_date.strftime("%H:%M") if task.due_date else "весь день"
                )
                categories = (
                    f" ({task.categories_display})" if task.categories.exists() else ""
                )
                message_parts.append(
                    f"{i}. <b>{task.title}</b>{categories} • ⏰ {time_str}"
                )

        # Статистика
        active_tasks = Task.objects.filter(user=user, completed=False).count()
        completed_tasks = Task.objects.filter(user=user, completed=True).count()
        total_tasks = active_tasks + completed_tasks

        message_parts.append("\n📊 <b>Ваша статистика:</b>")
        message_parts.append(f"• Активных задач: <b>{active_tasks}</b>")
        message_parts.append(f"• Выполнено: <b>{completed_tasks}</b>")

        if total_tasks > 0:
            completion_rate = int((completed_tasks / total_tasks) * 100)
            message_parts.append(f"• Прогресс: <b>{completion_rate}%</b>")

        # Подсказки
        message_parts.append("\n💡 <i>Быстрые команды:</i>")
        message_parts.append("• /tasks — все ваши задачи")
        message_parts.append("• /new — создать новую задачу")
        message_parts.append("• /stats — подробная статистика")

        message = "\n".join(message_parts)

        # Отправляем сообщение
        success = send_telegram_message_sync(telegram_id, message)

        if success:
            logger.info(f"✅ Ежедневное напоминание отправлено: {user.username}")
            return "✅ Напоминание отправлено"
        else:
            logger.error(f"❌ Не удалось отправить напоминание: {user.username}")
            return "❌ Не удалось отправить напоминание"

    except User.DoesNotExist:
        logger.error(f"❌ Пользователь {user_id} не найден")
        return "❌ Пользователь не найден"
    except Exception as e:
        logger.error(f"❌ Ошибка в send_user_daily_reminder: {e}")
        return f"❌ Ошибка: {e}"


@shared_task
def send_task_created_notification(task_id):
    """Уведомление о создании новой задачи"""
    try:
        task = (
            Task.objects.select_related("user", "user__profile")
            .prefetch_related("categories")
            .get(id=task_id)
        )

        telegram_id = get_user_telegram_id(task.user)

        if not telegram_id:
            return "❌ У пользователя нет telegram_id"

        message = f"""
✅ <b>НОВАЯ ЗАДАЧА СОЗДАНА!</b>

📌 <b>{task.title}</b>
📅 <b>Срок:</b> {task.due_date.strftime('%d.%m.%Y в %H:%M') if task.due_date else 'Не установлен'}
📝 <b>Описание:</b> {task.description or 'Нет описания'}

🆔 <b>ID задачи:</b> <code>{task.id}</code>
📋 <b>Создана:</b> {task.created_at.strftime('%d.%m.%Y %H:%M')}

<i>Удачи в выполнении! 🚀</i>
"""

        success = send_telegram_message_sync(telegram_id, message)

        if success:
            logger.info(f"✅ Уведомление о создании отправлено: {task.title}")
            return "✅ Уведомление о создании отправлено"
        else:
            return "❌ Не удалось отправить уведомление"

    except Exception as e:
        logger.error(f"❌ Ошибка в send_task_created_notification: {e}")
        return f"❌ Ошибка: {e}"


@shared_task
def send_task_completion_notification(task_id):
    """Уведомление о выполнении задачи"""
    try:
        task = (
            Task.objects.select_related("user", "user__profile")
            .prefetch_related("categories")
            .get(id=task_id)
        )

        telegram_id = get_user_telegram_id(task.user)

        if not telegram_id:
            return "❌ У пользователя нет telegram_id"

        # Статистика пользователя
        active_tasks = Task.objects.filter(user=task.user, completed=False).count()
        completed_tasks = Task.objects.filter(user=task.user, completed=True).count()
        total_tasks = active_tasks + completed_tasks

        completion_rate = (
            int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
        )

        message = f"""
🎉 <b>ЗАДАЧА ВЫПОЛНЕНА!</b>

✅ <b>{task.title}</b>
🏁 <b>Выполнена:</b> {timezone.now().strftime('%d.%m.%Y в %H:%M')}
📅 <b>Создана:</b> {task.created_at.strftime('%d.%m.%Y')}
⏳ <b>На выполнение:</b> {(timezone.now() - task.created_at).days} дней

📊 <b>Ваш прогресс:</b>
• Активных задач: <b>{active_tasks}</b>
• Выполнено: <b>{completed_tasks}</b>
• Прогресс: <b>{completion_rate}%</b>

<i>Отличная работа! Продолжайте в том же духе! 💪</i>
"""

        success = send_telegram_message_sync(telegram_id, message)

        if success:
            logger.info(f"✅ Уведомление о выполнении отправлено: {task.title}")
            return "✅ Уведомление о выполнении отправлено"
        else:
            return "❌ Не удалось отправить уведомление"

    except Exception as e:
        logger.error(f"❌ Ошибка в send_task_completion_notification: {e}")
        return f"❌ Ошибка: {e}"


@shared_task
def test_telegram_notification(user_id):
    """Тестовая задача для проверки Telegram уведомлений"""
    try:
        user = User.objects.select_related("profile").get(id=user_id)

        telegram_id = get_user_telegram_id(user)

        if not telegram_id:
            return f"❌ У пользователя {user.username} нет telegram_id"

        message = f"""
🔔 <b>ТЕСТ УВЕДОМЛЕНИЙ</b>

👋 Привет, {user.username}!

✅ <b>Все системы работают:</b>
• Telegram бот: <b>ОНЛАЙН</b>
• Celery задачи: <b>АКТИВНЫ</b>
• Уведомления: <b>ГОТОВЫ</b>

⏰ Время отправки: {timezone.now().strftime('%d.%m.%Y %H:%M:%S')}

<i>Тест пройден успешно! 🚀</i>
"""

        success = send_telegram_message_sync(telegram_id, message)

        if success:
            logger.info(f"✅ Тестовое уведомление отправлено: {user.username}")
            return "✅ Тестовое уведомление отправлено"
        else:
            return "❌ Не удалось отправить тестовое уведомление"

    except Exception as e:
        return f"❌ Ошибка теста: {e}"
