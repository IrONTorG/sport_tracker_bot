from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_panel_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура админ-панели
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🛑 Забанить пользователя",
            callback_data="admin_ban"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика всех",
            callback_data="admin_stats"
        ),
        InlineKeyboardButton(
            text="👥 Список пользователей",
            callback_data="admin_users_list"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔍 Поиск пользователя",
            callback_data="admin_search_user"
        )
    )

    return builder.as_markup()


def ban_confirm_kb(user_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения бана
    :param user_id: ID пользователя для бана
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, заблокировать",
            callback_data=f"ban_yes_{user_id}"
        ),
        InlineKeyboardButton(
            text="❌ Нет, отменить",
            callback_data="ban_no"
        )
    )

    return builder.as_markup()


def user_actions_kb(user_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура действий с пользователем
    :param user_id: ID пользователя
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🛑 Забанить",
            callback_data=f"admin_ban_{user_id}"
        ),
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data=f"admin_user_stats_{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✉️ Написать",
            callback_data=f"admin_message_{user_id}"
        ),
        InlineKeyboardButton(
            text="👑 Сделать админом",
            callback_data=f"admin_promote_{user_id}"
        )
    )

    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    """
    Кнопка возврата в админ-панель
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="← Назад",
            callback_data="admin_back"
        )
    )
    return builder.as_markup()