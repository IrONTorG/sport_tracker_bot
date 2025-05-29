from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_workout_types() -> ReplyKeyboardMarkup:
    """Клавиатура с типами тренировок"""
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="🏋️‍ Силовая"),
        KeyboardButton(text="🏃 Бег")
    )
    builder.row(
        KeyboardButton(text="🚴 Велосипед"),
        KeyboardButton(text="🧘 Йога")
    )
    builder.row(
        KeyboardButton(text="🏊 Плавание"),
        KeyboardButton(text="🤸 Прыжки на скакалке")
    )
    builder.row(KeyboardButton(text="❌ Отмена"))

    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True
    )