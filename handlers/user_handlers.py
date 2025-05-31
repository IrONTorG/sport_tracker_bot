import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db_session
from database.models import User, Workout
from keyboards.main_menu import get_main_menu

router = Router()


async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    """Вспомогательная функция для получения пользователя"""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()


async def get_user_stats(session: AsyncSession, user_id: int):
    """Получает статистику пользователя и его позицию в рейтинге"""
    # Статистика текущего пользователя
    workouts_count = await session.execute(
        select(func.count(Workout.workout_id)).where(Workout.user_id == user_id))
    workouts_count = workouts_count.scalar()

    total_duration = await session.execute(
        select(func.sum(Workout.duration)).where(Workout.user_id == user_id))
    total_duration = total_duration.scalar() or 0

    total_calories = await session.execute(
        select(func.sum(Workout.calories)).where(Workout.user_id == user_id))
    total_calories = total_calories.scalar() or 0

    # Позиция в рейтинге
    duration_rank = await session.execute(
        select(func.count(User.user_id))
        .select_from(User)
        .join(Workout)
        .group_by(User.user_id)
        .having(func.sum(Workout.duration) > total_duration)
    )
    duration_rank = duration_rank.scalar() or 0

    calories_rank = await session.execute(
        select(func.count(User.user_id))
        .select_from(User)
        .join(Workout)
        .group_by(User.user_id)
        .having(func.sum(Workout.calories) > total_calories)
    )
    calories_rank = calories_rank.scalar() or 0

    workouts_rank = await session.execute(
        select(func.count(User.user_id))
        .select_from(User)
        .join(Workout)
        .group_by(User.user_id)
        .having(func.count(Workout.workout_id) > (workouts_count or 0)
                ))
    workouts_rank = workouts_rank.scalar() or 0

    total_users = await session.execute(select(func.count(User.user_id)))
    total_users = total_users.scalar()

    return {
        'workouts_count': workouts_count or 0,
        'total_duration': total_duration,
        'total_calories': total_calories,
        'duration_rank': duration_rank + 1,
        'calories_rank': calories_rank + 1,
        'workouts_rank': workouts_rank + 1,
        'total_users': total_users
    }


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
@router.message(F.text == "👤 Мой профиль")
async def cmd_profile(message: Message):
    """Обработчик команды /profile и кнопки профиля"""
    async for session in get_db_session():
        try:
            user = await get_user(session, message.from_user.id)

            if user:
                stats = await get_user_stats(session, user.user_id)

                await message.answer(
                    f"👤 Ваш профиль:\n"
                    f"ID: {user.user_id}\n"
                    f"Имя: {user.name}\n"
                    f"Дата регистрации: {user.registration_date.strftime('%d.%m.%Y')}\n"
                    f"Статус: {'Администратор' if user.is_admin else 'Пользователь'}\n\n"
                    f"📊 Ваша статистика:\n"
                    f"Тренировок: {stats['workouts_count']}\n"
                    f"Общая длительность: {stats['total_duration']} мин\n"
                    f"Сожжено калорий: {stats['total_calories']}\n\n"
                    f"🏆 Ваше место в рейтинге:\n"
                    f"По длительности: {stats['duration_rank']}/{stats['total_users']}\n"
                    f"По калориям: {stats['calories_rank']}/{stats['total_users']}\n"
                    f"По количеству: {stats['workouts_rank']}/{stats['total_users']}"
                )
            else:
                await message.answer("Сначала запустите /start")
        except Exception as e:
            await message.answer("❌ Произошла ошибка при получении профиля")
            logging.error(f"Error in cmd_profile: {e}")