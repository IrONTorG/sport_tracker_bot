import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User
from database.session import get_db_session
from keyboards.admin import admin_panel_kb, ban_confirm_kb

router = Router()

async def get_user(session: AsyncSession, telegram_id: int):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Обработчик команды /admin"""
    async for session in get_db_session():
        try:
            user = await get_user(session, message.from_user.id)
            if not user or not user.is_admin:
                return await message.answer("🚫 Доступ запрещён!")
            await message.answer("👑 Админ-панель:", reply_markup=admin_panel_kb())
        except Exception as e:
            await message.answer("❌ Ошибка доступа к админ-панели")
            logging.error(f"Admin panel error: {e}")

@router.callback_query(F.data == "admin_ban")
async def show_ban_menu(callback: CallbackQuery):
    """Показывает меню бана пользователя"""
    async for session in get_db_session():
        try:
            admin = await get_user(session, callback.from_user.id)
            if not admin or not admin.is_admin:
                return await callback.answer("🚫 Доступ запрещён!", show_alert=True)

            user_id = 123  # Временный пример
            await callback.message.answer(
                f"🔨 Забанить пользователя {user_id}?",
                reply_markup=ban_confirm_kb(user_id)
            )
        except Exception as e:
            await callback.answer("❌ Ошибка при обработке запроса")
            logging.error(f"Ban menu error: {e}")

@router.callback_query(F.data.startswith("ban_"))
async def process_ban_callback(callback: CallbackQuery):
    """Обрабатывает подтверждение бана"""
    async for session in get_db_session():
        try:
            admin = await get_user(session, callback.from_user.id)
            if not admin or not admin.is_admin:
                return await callback.answer("🚫 Доступ запрещён!", show_alert=True)

            action, *data = callback.data.split('_')
            if action == "ban" and data[0] == "yes":
                user_id = int(data[1])
                user = await get_user(session, user_id)
                if user:
                    user.is_banned = True
                    await session.commit()
                    await callback.message.answer(f"✅ Пользователь {user_id} забанен.")
                else:
                    await callback.message.answer("❌ Пользователь не найден!")
        except Exception as e:
            await session.rollback()
            await callback.answer("❌ Ошибка при обработке бана")
            logging.error(f"Ban process error: {e}")
        finally:
            await callback.answer()