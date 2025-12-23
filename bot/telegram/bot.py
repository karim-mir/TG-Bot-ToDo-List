import asyncio
import logging
import os
import sys

import aiohttp
import django
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import (Dialog, DialogManager, ShowMode, Window,
                            setup_dialogs)
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Row, Start, SwitchTo
from aiogram_dialog.widgets.text import Case, Const, Format, Multi
from asgiref.sync import sync_to_async

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========== НАСТРОЙКА DJANGO В САМОМ НАЧАЛЕ ===========
# Настройка Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    django.setup()
    logger.info("✅ Django настроен успешно")
except Exception as e:
    logger.error(f"❌ Ошибка настройки Django: {e}")
    sys.exit(1)

# =========== ТЕПЕРЬ ИМПОРТИРУЕМ DJANGO МОДЕЛИ ===========
from django.contrib.auth.models import User

# =========== ИМПОРТ МОДЕЛЕЙ ИЗ ПРИЛОЖЕНИЯ ПОСЛЕ django.setup() ===========
try:
    from bot.models import UserProfile

    logger.info("✅ Модели бота импортированы успешно")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта моделей бота: {e}")
    # Создаем заглушку для UserProfile если не существует
    UserProfile = None


# =========== КЛАССЫ ===========
class TaskData:
    def __init__(self):
        self.title = None
        self.description = ""
        self.due_date = None
        self.category_ids = []
        self.user_id = None

    def __getitem__(self, key):
        """Позволяет использовать объект как словарь для Format"""
        if hasattr(self, key):
            return getattr(self, key)
        return None

    def to_dict(self):
        """Преобразует объект в словарь для отправки на API"""
        data = {
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "user": self.user_id,  # ✅ Важно: 'user', а не 'user_id'
        }

        # Добавляем категории если есть
        if self.category_ids:
            data["category_ids"] = [str(cid) for cid in self.category_ids]

        return data


# =========== СОСТОЯНИЯ ===========
class MainMenuSG(StatesGroup):
    MAIN = State()
    MY_TASKS = State()


class CreateTaskSG(StatesGroup):
    TITLE = State()
    DESCRIPTION = State()
    DUE_DATE = State()
    CATEGORIES = State()
    CONFIRM = State()
    COMPLETE = State()


# =========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===========
async def get_api_client():
    """Упрощенный API клиент"""
    base_url = "http://localhost:8000/api"

    class SimpleAPIClient:
        def __init__(self):
            self.base_url = base_url

        async def get_user_tasks(self, user_id):
            """Получить задачи пользователя - исправленная версия"""
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{self.base_url}/tasks/?user={user_id}"
                    logger.info(f"API GET: {url}")

                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()

                            # Извлекаем задачи из пагинированного ответа
                            if isinstance(data, dict) and "results" in data:
                                return data["results"]
                            elif isinstance(data, list):
                                return data
                            else:
                                logger.error(f"Неожиданный формат: {type(data)}")
                                return []

                return []

            except Exception as e:
                logger.error(f"Ошибка API: {e}")
                return []

        async def create_task(self, task_data):
            """Создать задачу - простая версия"""
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{self.base_url}/tasks/"
                    headers = {"Content-Type": "application/json"}

                    async with session.post(
                        url, json=task_data, headers=headers, timeout=10
                    ) as response:
                        if response.status in [200, 201]:
                            return await response.json()
                        else:
                            error = await response.text()
                            return {"error": error}

            except Exception as e:
                logger.error(f"Ошибка создания задачи: {e}")
                return {"error": str(e)}

    return SimpleAPIClient()


async def get_or_create_user(telegram_user):
    """Простая версия - создает пользователя с именем tg_user_<telegram_id>"""
    try:
        telegram_id = telegram_user.id
        username = f"tg_user_{telegram_id}"

        logger.info(f"Создание/поиск пользователя для Telegram ID: {telegram_id}")

        # Простое создание пользователя
        user, created = await sync_to_async(
            User.objects.get_or_create, thread_sensitive=True
        )(
            username=username,
            defaults={
                "first_name": telegram_user.first_name or "",
                "last_name": telegram_user.last_name or "",
                "email": f"{telegram_id}@telegram.user",
                "password": "simple_password",
            },
        )

        if created:
            logger.info(f"✅ Создан пользователь: {user.username} (ID: {user.id})")
        else:
            logger.info(f"✅ Найден пользователь: {user.username} (ID: {user.id})")

        return user, created

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        # Используем первого пользователя
        try:
            user = await sync_to_async(User.objects.first, thread_sensitive=True)()
            if user:
                return user, False
        except Exception as inner_e:  # ← ИСПРАВЛЕНО: было except:
            logger.error(f"Внутренняя ошибка: {inner_e}")
        return None, False


# =========== ОБРАБОТЧИКИ СОБЫТИЙ ===========
async def on_title_entered(
    message: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str
):
    """Обработка ввода заголовка"""
    logger.info(f"Title entered: {text}")
    if len(text.strip()) < 3:
        await message.answer("❌ Заголовок должен содержать минимум 3 символа")
        return

    task_data = dialog_manager.dialog_data.get("task_data", TaskData())
    task_data.title = text.strip()
    task_data.user_id = message.from_user.id
    dialog_manager.dialog_data["task_data"] = task_data
    await dialog_manager.next()


async def on_description_entered(
    message: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str
):
    """Минимальный обработчик создания задачи"""
    logger.info(f"Создание задачи: {text}")

    # Получаем данные задачи
    task_data = dialog_manager.dialog_data.get("task_data", TaskData())
    task_data.description = text.strip() if text else ""

    # Получаем пользователя
    telegram_user = message.from_user
    django_user, _ = await get_or_create_user(telegram_user)

    if not django_user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    # Устанавливаем пользователя
    task_data.user_id = django_user.id

    # Отправляем на сервер
    try:
        api_client = await get_api_client()
        task_dict = task_data.to_dict()

        result = await api_client.create_task(task_dict)

        # Простая проверка успеха
        if isinstance(result, dict) and "title" in result:
            await message.answer(f"✅ Задача '{result['title']}' создана!")
            logger.info(f"Задача создана: {result}")
        else:
            await message.answer("❌ Ошибка при создании задачи")
            logger.error(f"Ошибка: {result}")

    except Exception as e:
        await message.answer("❌ Ошибка соединения с сервером")
        logger.error(f"Сетевая ошибка: {e}")

    await dialog_manager.switch_to(CreateTaskSG.COMPLETE)


async def on_cancel_click(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Отмена создания задачи"""
    await callback.message.answer("❌ Создание задачи отменено")
    await dialog_manager.done()


async def on_refresh_tasks_click(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обновление списка задач"""
    await callback.answer("Обновляем список...")
    await dialog_manager.update({"force_refresh": True})


# =========== GETTER ФУНКЦИИ ===========
async def tasks_view_getter(dialog_manager: DialogManager, **kwargs):
    """Получает список задач пользователя с сервера"""
    telegram_user = dialog_manager.event.from_user

    try:
        # Получаем Django пользователя
        django_user, _ = await get_or_create_user(telegram_user)

        if not django_user:
            return {
                "tasks_display": "❌ Ошибка: пользователь не найден",
                "has_tasks": False,
                "tasks_count": 0,
            }

        logger.info(f"🔍 Поиск задач для пользователя ID: {django_user.id}")

        tasks = []
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://localhost:8000/api/tasks/?user={django_user.id}"
                logger.info(f"Запрос: {url}")

                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("✅ Получен ответ от API")

                        # ВАЖНО: API возвращает пагинированный ответ
                        # Нужно извлечь задачи из поля 'results'
                        if isinstance(data, dict) and "results" in data:
                            tasks = data["results"]
                            total_count = data.get("count", 0)
                            logger.info(
                                f"📊 Найдено {len(tasks)} задач (всего: {total_count})"
                            )
                        elif isinstance(data, list):
                            # Если API вернул просто список
                            tasks = data
                            logger.info(f"📊 Найдено {len(tasks)} задач")
                        else:
                            logger.error(f"Неожиданный формат ответа: {type(data)}")

        except Exception as e:
            logger.error(f"Ошибка запроса: {e}", exc_info=True)

        # Форматируем задачи
        if tasks and isinstance(tasks, list):
            tasks_display = ""
            for i, task in enumerate(tasks, 1):
                try:
                    if isinstance(task, dict):
                        title = task.get("title", "Без названия")
                        completed = "✅" if task.get("completed") else "⏳"
                        desc = task.get("description", "")

                        task_line = f"{i}. {title} {completed}"
                        if desc:
                            task_line += (
                                f"\n   📄 {desc[:50]}{'...' if len(desc) > 50 else ''}"
                            )

                        tasks_display += task_line + "\n\n"
                    else:
                        logger.warning(f"Задача {i} не словарь: {type(task)}")
                except Exception as e:
                    logger.error(f"Ошибка форматирования задачи {i}: {e}")

            return {
                "tasks_display": (
                    tasks_display if tasks_display else "📭 Нет задач для отображения"
                ),
                "has_tasks": len(tasks) > 0,
                "tasks_count": len(tasks),
            }
        else:
            return {
                "tasks_display": "📭 У вас пока нет задач",
                "has_tasks": False,
                "tasks_count": 0,
            }

    except Exception as e:
        logger.error(f"Ошибка в tasks_view_getter: {e}", exc_info=True)
        return {
            "tasks_display": "❌ Ошибка загрузки задач",
            "has_tasks": False,
            "tasks_count": 0,
        }


# =========== ДИАЛОГИ ===========
main_menu_dialog = Dialog(
    Window(
        Multi(
            Const("🏠 <b>Главное меню</b>"),
            Const(""),
            Const("Выберите действие:"),
            sep="\n",
        ),
        Row(
            Start(
                Const("📝 Создать задачу"), id="create_task", state=CreateTaskSG.TITLE
            ),
            SwitchTo(
                Const("📋 Мои задачи"), id="view_tasks", state=MainMenuSG.MY_TASKS
            ),
        ),
        state=MainMenuSG.MAIN,
    ),
    Window(
        Multi(
            Const("📋 <b>Мои задачи</b>"),
            Const(""),
            Format("📊 Всего задач: {tasks_count}"),
            Const(""),
            # Показываем задачи, если они есть
            Case(
                {
                    True: Multi(
                        Const("📝 <b>Ваши задачи:</b>"),
                        Const(""),
                        Format(
                            "{tasks_display}"
                        ),  # Просто выводим отформатированную строку
                        sep="\n",
                    ),
                    False: Const(
                        "📭 У вас пока нет задач. Создайте первую с помощью /new"
                    ),
                },
                selector="has_tasks",
            ),
            sep="\n",
        ),
        Row(
            SwitchTo(Const("◀️ Назад"), id="back", state=MainMenuSG.MAIN),
            Button(
                Const("🔄 Обновить"),
                id="refresh_tasks",
                on_click=on_refresh_tasks_click,
            ),
        ),
        state=MainMenuSG.MY_TASKS,
        getter=tasks_view_getter,
    ),
)

create_task_dialog = Dialog(
    Window(
        Multi(
            Const("📝 <b>Создание новой задачи</b>"),
            Const(""),
            Const("✏️ <b>Введите название задачи:</b>"),
            Const("(минимум 3 символа)"),
            sep="\n",
        ),
        TextInput(
            id="title_input",
            on_success=on_title_entered,
        ),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_click),
        state=CreateTaskSG.TITLE,
    ),
    Window(
        Multi(
            Const("📝 <b>Создание новой задачи</b>"),
            Const(""),
            Const("📌 <b>Название:</b>"),
            Format("{dialog_data[task_data][title]}"),
            Const(""),
            Const("📄 <b>Введите описание (необязательно):</b>"),
            sep="\n",
        ),
        TextInput(
            id="description_input",
            on_success=on_description_entered,
        ),
        Row(
            SwitchTo(Const("◀️ Назад"), id="back", state=CreateTaskSG.TITLE),
            Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_click),
        ),
        state=CreateTaskSG.DESCRIPTION,
    ),
    Window(
        Multi(
            Const("✅ <b>Задача создана!</b>"),
            Const(""),
            Const("📌 <b>Название:</b>"),
            Format("{dialog_data[task_data][title]}"),
            Const(""),
            Const("📄 <b>Описание:</b>"),
            Format("{dialog_data[task_data][description]}"),
            sep="\n",
        ),
        Row(
            Start(Const("📝 Новая задача"), id="new_task", state=CreateTaskSG.TITLE),
            Start(Const("🏠 В меню"), id="to_menu", state=MainMenuSG.MAIN),
        ),
        state=CreateTaskSG.COMPLETE,
    ),
)


# =========== ОСНОВНАЯ ФУНКЦИЯ ===========
async def main():
    """Основная функция запуска бота"""
    # Инициализация бота
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN не найден")
        return

    logger.info("Инициализация бота...")

    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode="HTML"))

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Включаем диалоги
    logger.info("Регистрация диалогов...")
    dp.include_router(main_menu_dialog)
    dp.include_router(create_task_dialog)
    logger.info(f"main_menu_dialog окна: {list(main_menu_dialog.windows.keys())}")

    # Настраиваем диалоги
    setup_dialogs(dp)

    # Обработчик команды /start
    @dp.message(Command("start"))
    async def start_handler(message: types.Message, dialog_manager: DialogManager):
        telegram_user = message.from_user
        logger.info(f"START HANDLER: User {telegram_user.id} sent /start")

        user, is_new = await get_or_create_user(telegram_user)

        if not user:
            await message.answer("❌ Ошибка регистрации")
            return

        if is_new:
            response = f"👋 Добро пожаловать, {telegram_user.first_name or 'друг'}!"
        else:
            response = f"👋 С возвращением, {telegram_user.first_name or 'друг'}!"

        await message.answer(response)
        await dialog_manager.start(MainMenuSG.MAIN, show_mode=ShowMode.EDIT)

    # Обработчик команды /menu
    @dp.message(Command("menu"))
    async def menu_handler(message: types.Message, dialog_manager: DialogManager):
        logger.info(f"MENU HANDLER: User {message.from_user.id} sent /menu")
        await dialog_manager.start(MainMenuSG.MAIN, show_mode=ShowMode.EDIT)

    # Обработчик команды /help
    @dp.message(Command("help"))
    async def help_handler(message: types.Message):
        logger.info(f"HELP HANDLER: User {message.from_user.id} sent /help")
        help_text = """
📋 <b>ToDo List Bot - Команды</b>

• /start - начать работу
• /menu - главное меню
• /new - новая задача
• /tasks - мои задачи
• /help - справка
"""
        await message.answer(help_text)

    # Обработчик команды /new
    @dp.message(Command("new"))
    async def new_handler(message: types.Message, dialog_manager: DialogManager):
        logger.info(f"NEW HANDLER: User {message.from_user.id} sent /new")
        try:
            await dialog_manager.start(CreateTaskSG.TITLE, show_mode=ShowMode.EDIT)
            logger.info("Create task dialog started successfully")
        except Exception as e:
            logger.error(f"Error starting create task dialog: {e}", exc_info=True)
            await message.answer(f"❌ Ошибка запуска создания задачи: {e}")

    # Обработчик команды /tasks
    @dp.message(Command("tasks"))
    async def tasks_handler(message: types.Message, dialog_manager: DialogManager):
        logger.info(f"TASKS HANDLER: User {message.from_user.id} sent /tasks")
        try:
            await dialog_manager.start(MainMenuSG.MY_TASKS, show_mode=ShowMode.EDIT)
            logger.info("Tasks dialog started successfully")
        except Exception as e:
            logger.error(f"Error starting tasks dialog: {e}", exc_info=True)
            await message.answer(f"❌ Ошибка запуска списка задач: {e}")

    # Обработчик команды /test
    @dp.message(Command("test"))
    async def test_handler(message: types.Message):
        logger.info(f"TEST HANDLER: User {message.from_user.id} sent /test")
        await message.answer("✅ Тестовая команда работает!")

    # Запуск бота
    logger.info("Запуск бота...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
