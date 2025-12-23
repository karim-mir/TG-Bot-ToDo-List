# 🤖 Telegram Bot ToDo List

Проект представляет собой систему управления задачами с интеграцией Telegram бота, веб-интерфейсом и фоновыми задачами через Celery.

## 🚀 Возможности

- 📝 Создание, редактирование и удаление задач через Telegram бота
- 🔔 Уведомления о дедлайнах задач
- 📊 Веб-интерфейс для управления задачами (Django Admin)
- ⏰ Автоматические напоминания через Celery Beat
- 🐳 Полная контейнеризация с Docker
- 🔄 Фоновая обработка задач через Celery Worker
- 📱 REST API для интеграции с другими системами

## 🏗️ Архитектура

Проект построен на микросервисной архитектуре с использованием:

- **Django** - веб-фреймворк
- **PostgreSQL** - основная база данных
- **Redis** - брокер сообщений для Celery
- **Celery** - распределенная очередь задач
- **Docker** - контейнеризация
- **Telegram Bot API** - интеграция с мессенджером

## 📁 Структура проекта
```commandline
├── bot/ # Приложение Telegram бота
│ ├── models.py # Модели данных
│ ├── tasks.py # Celery задачи
│ ├── views.py # API представления
│ └── telegram/ # Логика Telegram бота
├── config/ # Конфигурация Django
│ ├── settings.py # Настройки
│ ├── celery.py # Конфигурация Celery
│ └── urls.py # Маршруты API
├── docker-compose.yml # Docker Compose конфигурация
├── Dockerfile # Docker образ
├── .env # Переменные окружения
├── manage.py # Django CLI
└──pyproject.toml # Зависимости (Poetry)
```
## 🛠️ Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Python 3.12+ (для локальной разработки)
- Telegram бот (получить токен у @BotFather)

### 1. Клонирование репозитория

```
git clone https://github.com/karim-mir/TG-Bot-ToDo-List
```
### 2. Настройка окружения
- Создайте файл .env на основе .env.example
- Отредактируйте .env файл, указав свои настройки:
```
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,web

# Database
DB_NAME=TG_Bot_ToDo_List
DB_USER=postgres
DB_PASSWORD=your-password

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```
### 3. Запуск в Docker

```commandline
# Сборка и запуск контейнеров
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```
# 🔧 Конфигурация
## Переменные окружения
### 1. Основные переменные окружения, которые можно настроить в .env файле:
```
SECRET_KEY - секретный ключ Django
DEBUG - режим отладки (True/False)
TELEGRAM_BOT_TOKEN - токен Telegram бота
DB_* - настройки базы данных PostgreSQL
REDIS_* - настройки Redis
```
### 2. Настройка Telegram бота

- Создайте бота через @BotFather
- Получите токен
- Добавьте токен в .env файл:

```
TELEGRAM_BOT_TOKEN=your_token_here
```
# 📡 API эндпоинты
## Проект предоставляет REST API с документацией Swagger:

http://localhost:8000/api/ - основной API

http://localhost:8000/swagger/ - документация Swagger

http://localhost:8000/admin/ - административная панель Django

# 🎯 Использование
## Через Telegram бота

### 1. Найдите вашего бота в Telegram `@tgbottodolist_bot`

### 2. Отправьте команду /start для регистрации

- Используйте команды:

```
/new - добавить задачу
/list - список задач
/hepl - для вывода всех досупных команд
```

### 3. Через веб-интерфейс

- Откройте http://localhost:8000/admin/

- Войдите с данными суперпользователя

- Управляйте задачами и пользователями