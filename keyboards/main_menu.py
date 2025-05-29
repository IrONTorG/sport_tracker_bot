from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu(user_is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Создает главное меню с учетом прав пользователя

    :param user_is_admin: Флаг, является ли пользователь администратором
    :return: Объект ReplyKeyboardMarkup с главным меню
    """
    builder = ReplyKeyboardBuilder()

    # Основные кнопки для всех пользователей
    builder.row(
        KeyboardButton(text="📋 Мои тренировки"),
        KeyboardButton(text="📊 Моя статистика")
    )
    builder.row(
        KeyboardButton(text="🔔 Мои напоминания"),
        KeyboardButton(text="⚙️ Настройки")
    )
    builder.row(
        KeyboardButton(text="ℹ️ Помощь")
    )


    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


def get_cancel_kb() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
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