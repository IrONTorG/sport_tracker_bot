from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu(user_is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    # Основные кнопки для всех пользователей
    builder.row(
        KeyboardButton(text="📋 Мои тренировки"),
        KeyboardButton(text="📊 Моя статистика")
    )
    builder.row(
        KeyboardButton(text="👤 Мой профиль"),
        KeyboardButton(text="🔔 Мои напоминания")
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="ℹ️ Помощь")
    )
    # Добавляем кнопку админ-панели только для админов
    if user_is_admin:
        builder.row(KeyboardButton(text="👑 Админ-панель"))

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


def get_settings_menu(notifications_enabled: bool = True) -> ReplyKeyboardMarkup:
    """Клавиатура настроек"""
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="👤 Изменить имя"),
        KeyboardButton(text="🔔 Управление уведомлениями")
    )
    builder.row(
        KeyboardButton(text="📨 Связаться с админом"),
        KeyboardButton(text="🗑️ Удалить аккаунт")
    )
    builder.row(
        KeyboardButton(text="🔙 Главное меню")
    )

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите настройку..."
    )


def get_workout_types_kb() -> ReplyKeyboardMarkup:
    """Клавиатура с типами тренировок"""
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="🏃 Бег"),
        KeyboardButton(text="🚴 Велосипед")
    )
    builder.row(
        KeyboardButton(text="🏋️‍ Силовая"),
        KeyboardButton(text="🧘 Йога")
    )
    builder.row(
        KeyboardButton(text="🏊 Плавание"),
        KeyboardButton(text="🤸 Другое")
    )
    builder.row(KeyboardButton(text="❌ Отмена"))

    return builder.as_markup(resize_keyboard=True)


def get_workout_pagination_kb(has_prev: bool, has_next: bool) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    if has_prev:
        builder.add(KeyboardButton(text="⬅️ Назад"))
    if has_next:
        builder.add(KeyboardButton(text="➡️ Вперед"))

    builder.row()
    builder.row(
        KeyboardButton(text="➕ Добавить тренировку"),
        KeyboardButton(text="✏️ Редактировать"),
        KeyboardButton(text="🗑️ Удалить")
    )
    builder.row(KeyboardButton(text="🔙 Главное меню"))

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


def get_help_text() -> str:
    """Возвращает форматированный текст помощи"""
    return (
        "🤖 <b>Telegram бот для учета тренировок</b>\n\n"
        "🔹 <b>Разработан</b> на базе:\n"
        "- Python 3.11\n"
        "- Aiogram 3.x (асинхронный фреймворк для Telegram ботов)\n"
        "- SQLAlchemy 2.0 (ORM для работы с базой данных)\n"
        "- PostgreSQL (реляционная СУБД)\n\n"
        "🔹 <b>Основные функции:</b>\n"
        "📋 <b>Мои тренировки</b> - добавление, редактирование и просмотр ваших тренировок\n"
        "📊 <b>Моя статистика</b> - анализ вашей активности и прогресса\n"
        "👤 <b>Мой профиль</b> - информация о вашем аккаунте и достижениях\n"
        "🔔 <b>Мои напоминания</b> - настройка уведомлений о тренировках\n"
        "⚙️ <b>Настройки</b> - персонализация вашего опыта\n\n"
        "🔹 <b>Дополнительные возможности:</b>\n"
        "- Рейтинги и сравнение с другими пользователями\n"
        "- Разные типы тренировок (бег, велоспорт, силовые и др.)\n"
        "- Визуализация статистики\n"
        "- Гибкая система напоминаний\n\n"
        "📝 <b>Разработчик</b>: @IrONTorG\n"
        "🎓 Разработано в рамках научно-исследовательской работы\n"
        "🏫 Воронежский Государственный Университет, ФКН ПРИНЖ, 3 курс\n\n"
        "По всем вопросам и предложениям обращайтесь к разработчику!"
    )