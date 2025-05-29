from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_stats_period_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода статистики"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📅 За день",
            callback_data="stats_day"
        ),
        InlineKeyboardButton(
            text="📆 За неделю",
            callback_data="stats_week"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🗓️ За месяц",
            callback_data="stats_month"
        ),
        InlineKeyboardButton(
            text="📅 За всё время",
            callback_data="stats_all"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 Экспорт в CSV",
            callback_data="export_csv"
        ),
        InlineKeyboardButton(
            text="📊 Экспорт в JSON",
            callback_data="export_json"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📈 График прогресса",
            callback_data="show_progress"
        )
    )

    return builder.as_markup()