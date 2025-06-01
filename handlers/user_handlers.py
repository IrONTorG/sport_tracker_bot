import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, \
    KeyboardButton
from aiogram.filters import Command
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db_session
from database.models import User, Workout, Exercise, Reminder
from keyboards.main_menu import get_main_menu, get_help_text, get_settings_menu
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import UserStates

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

@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    """Обработчик кнопки помощи"""
    from keyboards.main_menu import get_help_text
    await message.answer(
        get_help_text(),
        parse_mode="HTML"
    )


@router.message(F.text == "📨 Связаться с админом")
async def contact_admin(message: Message):
    """Обработчик кнопки связи с администратором"""
    admin_id = 644959718  # Ваш Telegram ID
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Написать администратору",
        url=f"tg://user?id={admin_id}")
    )

    await message.answer(
        "Вы можете связаться с администратором напрямую:",
        reply_markup=builder.as_markup()
    )


@router.message(F.text == "🗑️ Удалить аккаунт")
async def delete_account_confirmation(message: Message):
    """Запрос подтверждения на удаление аккаунта"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete"),
        InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_delete")
    )

    await message.answer(
        "⚠️ <b>Внимание!</b> Вы действительно хотите удалить свой аккаунт?\n"
        "Это действие удалит все ваши данные, включая тренировки и напоминания, и не может быть отменено.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_delete")
async def delete_account(callback: CallbackQuery):
    """Обработчик удаления аккаунта"""
    async for session in get_db_session():
        try:
            user = await get_user(session, callback.from_user.id)
            if not user:
                return await callback.answer("❌ Аккаунт не найден", show_alert=True)

            # Удаляем все связанные данные пользователя
            await session.execute(delete(Exercise).where(Exercise.workout_id.in_(
                select(Workout.workout_id).where(Workout.user_id == user.user_id)
            )))
            await session.execute(delete(Workout).where(Workout.user_id == user.user_id))
            await session.execute(delete(Reminder).where(Reminder.user_id == user.user_id))
            await session.execute(delete(User).where(User.user_id == user.user_id))

            await session.commit()

            await callback.message.edit_text(
                "✅ Ваш аккаунт и все данные успешно удалены.\n"
                "Для нового использования бота нажмите /start"
            )
        except Exception as e:
            await session.rollback()
            await callback.answer("❌ Ошибка при удалении аккаунта", show_alert=True)
            logging.error(f"Error deleting account: {e}")


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    """Отмена удаления аккаунта"""
    await callback.message.edit_text("❌ Удаление аккаунта отменено")

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    """Показывает меню настроек"""
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Выберите нужный пункт:",
        reply_markup=get_settings_menu(),
        parse_mode="HTML"
    )

@router.message(F.text == "👤 Изменить имя")
async def change_name(message: Message, state: FSMContext):
    """Запрос на изменение имени"""
    await message.answer(
        "✏️ Введите новое имя:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(UserStates.waiting_for_new_name)

@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer(
        "Действие отменено",
        reply_markup=get_main_menu()
    )

@router.message( F.text == "🔙 Главное меню")
async def return_to_menu_from_pagination(message: Message, state: FSMContext):
    """Возврат в главное меню из режима просмотра"""
    async for session in get_db_session():
        user = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id))
        user = user.scalar_one()
        await state.clear()
        await message.answer(
            "Главное меню:",
            reply_markup=get_main_menu(user.is_admin)
        )

@router.message(UserStates.waiting_for_new_name)
async def process_new_name(message: Message, state: FSMContext):
    """Обработка нового имени"""
    new_name = message.text.strip()
    if len(new_name) < 2:
        return await message.answer("❌ Имя слишком короткое, попробуйте еще раз")

    async for session in get_db_session():
        try:
            user = await get_user(session, message.from_user.id)
            if user:
                user.name = new_name
                await session.commit()
                await message.answer(
                    f"✅ Имя успешно изменено на: {new_name}",
                    reply_markup=get_main_menu(user.is_admin)
                )
            else:
                await message.answer("❌ Пользователь не найден")
        except Exception as e:
            await session.rollback()
            await message.answer("❌ Ошибка при изменении имени")
            logging.error(f"Error changing name: {e}")
    await state.clear()