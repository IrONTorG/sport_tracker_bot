from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_panel_kb() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🛑 Бан/Разбан",
            callback_data="admin_ban"
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
        ),
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="admin_stats"
        )
    )

    return builder.as_markup()


def users_list_kb(users: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура со списком пользователей с пагинацией"""
    builder = InlineKeyboardBuilder()

    for user in users:
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {user.name} (ID: {user.telegram_id})",
                callback_data=f"user_select_{user.telegram_id}"
            )
        )

    # Кнопки пагинации
    pagination_row = []
    if page > 1:
        pagination_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"users_page_{page - 1}"))

    pagination_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="current_page"))

    if page < total_pages:
        pagination_row.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"users_page_{page + 1}"))

    builder.row(*pagination_row)

    builder.row(
        InlineKeyboardButton(
            text="⬅️ В админ-панель",
            callback_data="admin_back"
        )
    )

    return builder.as_markup()


def ban_confirm_kb(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения бана/разбана"""
    builder = InlineKeyboardBuilder()

    action = "разбанить" if is_banned else "забанить"

    builder.row(
        InlineKeyboardButton(
            text=f"✅ Да, {action}",
            callback_data=f"ban_confirm_{user_id}"
        ),
        InlineKeyboardButton(
            text="❌ Нет, отменить",
            callback_data="admin_back"
        )
    )

    return builder.as_markup()


def user_actions_kb(user_id: int, is_banned: bool, is_admin: bool) -> InlineKeyboardMarkup:
    """Клавиатура действий с пользователем"""
    builder = InlineKeyboardBuilder()

    ban_text = "🔓 Разбанить" if is_banned else "🛑 Забанить"
    admin_text = "👑 Снять админа" if is_admin else "👑 Сделать админом"

    builder.row(
        InlineKeyboardButton(
            text=ban_text,
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
            text=admin_text,
            callback_data=f"admin_promote_{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ В админ-панель",
            callback_data="admin_back"
        )
    )

    return builder.as_markup()


def stats_options_kb() -> InlineKeyboardMarkup:
    """Клавиатура опций статистики"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📈 График тренировок",
            callback_data="stats_graph"
        ),
        InlineKeyboardButton(
            text="📊 Общие цифры",
            callback_data="stats_numbers"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📤 Экспорт данных",
            callback_data="stats_export"
        ),
        InlineKeyboardButton(
            text="⬅️ В админ-панель",
            callback_data="admin_back"
        )
    )

    return builder.as_markup()


def export_format_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора формата экспорта"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="CSV",
            callback_data="export_csv"
        ),
        InlineKeyboardButton(
            text="JSON",
            callback_data="export_json"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="stats_back"
        )
    )

    return builder.as_markup()


def stats_back_kb() -> InlineKeyboardMarkup:
    """Клавиатура возврата в меню статистики"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ В меню статистики",
            callback_data="stats_back"
        )
    )
    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в админ-панель"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ В админ-панель",
            callback_data="admin_back"
        )
    )
    return builder.as_markup()