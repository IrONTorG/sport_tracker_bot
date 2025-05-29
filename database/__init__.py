"""
Инициализация модуля database.
Экспортирует основные компоненты для работы с БД:
- Базовый класс моделей Base
- Функцию получения сессии get_db
- Движок подключения engine
- Все модели (User, Workout, Exercise, Reminder)
"""

from .session import Base, get_db_session, engine, check_db_connection
from .models import (
    User,
    Workout,
    Exercise,
    Reminder
)

__all__ = [
    'Base',
    'get_db_session',  # Изменили с get_db на get_db_session
    'engine',
    'User',
    'Workout',
    'Exercise',
    'Reminder'
]


async def check_connection():
    """Проверяет подключение к БД при импорте"""
    try:
        await check_db_connection()
        print("✅ Подключение к БД успешно")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")