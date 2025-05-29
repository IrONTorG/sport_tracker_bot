import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db_session
from database.models import User
from keyboards.main_menu import get_main_menu

router = Router()

async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    """Вспомогательная функция для получения пользователя"""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    async for session in get_db_session():
        try:
            user = await get_user(session, message.from_user.id)

            if not user:
                new_user = User(
                    telegram_id=message.from_user.id,
                    name=message.from_user.full_name
                )
                session.add(new_user)
                await session.commit()
                await message.answer(
                    "👋 Привет! Я бот для учёта тренировок.",
                    reply_markup=get_main_menu()
                )
            else:
                await message.answer(
                    "🔄 С возвращением!",
                    reply_markup=get_main_menu(user.is_admin)
                )
        except Exception as e:
            await session.rollback()
            await message.answer("❌ Произошла ошибка, попробуйте позже")
            logging.error(f"Error in cmd_start: {e}")

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Обработчик команды /profile"""
    async for session in get_db_session():
        try:
            user = await get_user(session, message.from_user.id)

            if user:
                await message.answer(
                    f"👤 Ваш профиль:\n"
                    f"ID: {user.user_id}\n"
                    f"Имя: {user.name}\n"
                    f"Дата регистрации: {user.registration_date.strftime('%d.%m.%Y')}\n"
                    f"Статус: {'Администратор' if user.is_admin else 'Пользователь'}"
                )
            else:
                await message.answer("Сначала запустите /start")
        except Exception as e:
            await message.answer("❌ Произошла ошибка при получении профиля")
            logging.error(f"Error in cmd_profile: {e}")