from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import (
    ReplyKeyboardBuilder,
    InlineKeyboardBuilder
)

def get_weekdays_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="Понедельник"),
        KeyboardButton(text="Вторник"),
        KeyboardButton(text="Среда")
    )
    builder.row(
        KeyboardButton(text="Четверг"),
        KeyboardButton(text="Пятница"),
        KeyboardButton(text="Суббота")
    )
    builder.row(
        KeyboardButton(text="Воскресенье"),
        KeyboardButton(text="❌ Отмена")
    )
    return builder.as_markup(resize_keyboard=True)

# Клавиатура подтверждения (Inline)
def confirm_reminder_kb(reminder_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"rem_confirm_{reminder_id}"
        ),
        InlineKeyboardButton(
            text="✏️ Изменить",
            callback_data=f"rem_edit_{reminder_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Удалить",
            callback_data=f"rem_delete_{reminder_id}"
        )
    )

    return builder.as_markup()


# Клавиатура управления напоминаниями (Inline)
def reminders_control_kb(reminders: list = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ Создать напоминание",
            callback_data="rem_create_new"
        )
    )

    if reminders:  # Если есть напоминания - показываем их и кнопку удалить все
        for rem in reminders:
            builder.row(
                InlineKeyboardButton(
                    text=f"{rem['day']} в {rem['time']} - {rem['text']}",
                    callback_data=f"rem_view_{rem['id']}"
                )
            )
        builder.row(
            InlineKeyboardButton(
                text="🗑️ Удалить все",
                callback_data="rem_delete_all"
            )
        )
    else:  # Если нет напоминаний - только кнопку создания
        builder.row(
            InlineKeyboardButton(
                text="📋 Мои напоминания",
                callback_data="rem_my_reminders"
            )
        )

    return builder.as_markup()


# Клавиатура редактирования (Inline)
def edit_reminder_kb(reminder_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✏️ Текст",
            callback_data=f"rem_edit_text_{reminder_id}"
        ),
        InlineKeyboardButton(
            text="🕒 Время",
            callback_data=f"rem_edit_time_{reminder_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📅 День",
            callback_data=f"rem_edit_day_{reminder_id}"
        ),
        InlineKeyboardButton(
            text="❌ Удалить",
            callback_data=f"rem_delete_{reminder_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="← Назад",
            callback_data="rem_my_reminders"
        )
    )

    return builder.as_markup()


# Клавиатура частых времен (Reply)
def common_times_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    times = [
        "06:00", "08:00", "12:00",
        "15:00", "18:00", "21:00"
    ]

    for time in times:
        builder.add(KeyboardButton(text=time))

    builder.row(KeyboardButton(text="❌ Отмена"))

    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True
    )


# Клавиатура включения/выключения (Inline)
def toggle_reminder_kb(reminder_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔔 Включено" if is_active else "🔕 Выключено",
            callback_data=f"rem_toggle_{reminder_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="← К списку",
            callback_data="rem_back_to_list"
        )
    )

    return builder.as_markup()