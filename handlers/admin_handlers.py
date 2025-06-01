import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Workout, Exercise
from database.session import get_db_session
from keyboards.admin import (
    admin_panel_kb, ban_confirm_kb, users_list_kb,
    user_actions_kb, stats_options_kb, export_format_kb,
    admin_back_kb, stats_back_kb
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import csv
import json
from aiogram.types.input_file import BufferedInputFile

router = Router()


class AdminStates(StatesGroup):
    waiting_for_ban_user = State()
    waiting_for_user_search = State()
    waiting_for_export_format = State()
    waiting_for_user_message = State()


async def get_user(session: AsyncSession, telegram_id: int):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()


async def get_user_stats(session: AsyncSession, user_id: int):
    workouts_count = await session.execute(
        select(func.count(Workout.workout_id)).where(Workout.user_id == user_id))
    workouts_count = workouts_count.scalar()

    total_duration = await session.execute(
        select(func.sum(Workout.duration)).where(Workout.user_id == user_id))
    total_duration = total_duration.scalar() or 0

    total_calories = await session.execute(
        select(func.sum(Workout.calories)).where(Workout.user_id == user_id))
    total_calories = total_calories.scalar() or 0

    return {
        'workouts_count': workouts_count,
        'total_duration': total_duration,
        'total_calories': total_calories
    }


async def get_global_stats(session: AsyncSession):
    users_count = await session.execute(select(func.count(User.user_id)))
    users_count = users_count.scalar()

    workouts_count = await session.execute(select(func.count(Workout.workout_id)))
    workouts_count = workouts_count.scalar()

    total_duration = await session.execute(select(func.sum(Workout.duration)))
    total_duration = total_duration.scalar() or 0

    total_calories = await session.execute(select(func.sum(Workout.calories)))
    total_calories = total_calories.scalar() or 0

    return {
        'users_count': users_count,
        'workouts_count': workouts_count,
        'total_duration': total_duration,
        'total_calories': total_calories
    }


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Обработчик команды /admin"""
    async for session in get_db_session():
        try:
            user = await get_user(session, message.from_user.id)
            if not user or not user.is_admin:
                return await message.answer("🚫 Доступ запрещён!")

            await message.answer(
                "👑 Админ-панель",
                reply_markup=admin_panel_kb()
            )
        except Exception as e:
            logging.error(f"Admin panel error: {e}")


@router.message(F.text == "👑 Админ-панель")
async def admin_panel_button(message: Message):
    await admin_panel(message)


@router.callback_query(F.data == "admin_back")
async def handle_admin_back(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "👑 Админ-панель",
        reply_markup=admin_panel_kb()
    )


@router.callback_query(F.data == "admin_ban")
async def show_ban_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "Введите ID или username пользователя (@username):",
        reply_markup=admin_back_kb()
    )
    await state.set_state(AdminStates.waiting_for_ban_user)


@router.message(AdminStates.waiting_for_ban_user)
async def process_ban_user(message: Message, state: FSMContext):
    user_input = message.text.strip()
    async for session in get_db_session():
        try:
            admin = await get_user(session, message.from_user.id)
            if not admin or not admin.is_admin:
                return await message.answer("🚫 Доступ запрещён!")

            user = None
            if user_input.isdigit():
                user = await session.execute(
                    select(User).where(User.telegram_id == int(user_input)))
                user = user.scalars().first()
            elif user_input.startswith("@"):
                username = user_input[1:]
                user = await session.execute(
                    select(User).where(User.username == username))
                user = user.scalars().first()

            if not user:
                return await message.answer("❌ Пользователь не найден!")

            await message.answer(
                f"Вы действительно хотите {'разбанить' if user.is_banned else 'забанить'} пользователя {user.name}?",
                reply_markup=ban_confirm_kb(user.telegram_id, user.is_banned)
            )
            await state.clear()
        except Exception as e:
            logging.error(f"Ban process error: {e}")


@router.callback_query(F.data.startswith("ban_confirm_"))
async def process_ban_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])

    async for session in get_db_session():
        try:
            admin = await get_user(session, callback.from_user.id)
            if not admin or not admin.is_admin:
                return await callback.answer("🚫 Доступ запрещён!", show_alert=True)

            user = await session.execute(
                select(User).where(User.telegram_id == user_id))
            user = user.scalars().first()

            if not user:
                return await callback.answer("❌ Пользователь не найден!", show_alert=True)

            user.is_banned = not user.is_banned
            await session.commit()

            action = "забанен" if user.is_banned else "разбанен"
            await callback.message.edit_text(
                f"✅ Пользователь {user.name} {action}.",
                reply_markup=admin_back_kb()
            )
        except Exception as e:
            await session.rollback()
            logging.error(f"Ban process error: {e}")


@router.callback_query(F.data == "admin_users_list")
async def show_users_list(callback: CallbackQuery, page: int = 1):
    await callback.answer()
    async for session in get_db_session():
        try:
            admin = await get_user(session, callback.from_user.id)
            if not admin or not admin.is_admin:
                return await callback.answer("🚫 Доступ запрещён!", show_alert=True)

            users_per_page = 5
            offset = (page - 1) * users_per_page

            total_users = await session.execute(select(func.count(User.user_id)))
            total_users = total_users.scalar()
            total_pages = (total_users + users_per_page - 1) // users_per_page

            users = await session.execute(
                select(User)
                .order_by(User.registration_date.desc())
                .offset(offset)
                .limit(users_per_page)
            )
            users = users.scalars().all()

            await callback.message.edit_text(
                f"👥 Список пользователей (страница {page}/{total_pages}):",
                reply_markup=users_list_kb(users, page, total_pages)
            )
        except Exception as e:
            logging.error(f"Users list error: {e}")


@router.callback_query(F.data.startswith("users_page_"))
async def handle_users_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await show_users_list(callback, page)


@router.callback_query(F.data.startswith("user_select_"))
async def handle_user_select(callback: CallbackQuery):
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])

    async for session in get_db_session():
        try:
            admin = await get_user(session, callback.from_user.id)
            if not admin or not admin.is_admin:
                return await callback.answer("🚫 Доступ запрещён!", show_alert=True)

            user = await get_user(session, user_id)
            if not user:
                return await callback.answer("❌ Пользователь не найден!", show_alert=True)

            stats = await get_user_stats(session, user.user_id)

            await callback.message.edit_text(
                f"👤 Информация о пользователе:\n"
                f"ID: {user.user_id}\n"
                f"Telegram ID: {user.telegram_id}\n"
                f"Имя: {user.name}\n"
                f"Дата регистрации: {user.registration_date.strftime('%d.%m.%Y %H:%M')}\n"
                f"Статус: {'Администратор' if user.is_admin else 'Пользователь'}\n"
                f"Бан: {'Да' if user.is_banned else 'Нет'}\n\n"
                f"📊 Статистика:\n"
                f"Тренировок: {stats['workouts_count']}\n"
                f"Общая длительность: {stats['total_duration']} мин\n"
                f"Сожжено калорий: {stats['total_calories']}",
                reply_markup=user_actions_kb(user.telegram_id, user.is_banned, user.is_admin)
            )
        except Exception as e:
            logging.error(f"User select error: {e}")


@router.callback_query(F.data == "admin_stats")
async def show_stats_options(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "📊 Выберите тип статистики:",
        reply_markup=stats_options_kb()
    )


@router.callback_query(F.data == "stats_numbers")
async def show_global_stats(callback: CallbackQuery):
    await callback.answer()
    async for session in get_db_session():
        try:
            admin = await get_user(session, callback.from_user.id)
            if not admin or not admin.is_admin:
                return await callback.answer("🚫 Доступ запрещён!", show_alert=True)

            stats = await get_global_stats(session)

            top_duration = await session.execute(
                select(User.name, func.sum(Workout.duration).label('total'))
                .join(Workout)
                .group_by(User.user_id)
                .order_by(func.sum(Workout.duration).desc())
                .limit(5)
            )
            top_duration = top_duration.all()

            top_calories = await session.execute(
                select(User.name, func.sum(Workout.calories).label('total'))
                .join(Workout)
                .group_by(User.user_id)
                .order_by(func.sum(Workout.calories).desc())
                .limit(5)
            )
            top_calories = top_calories.all()

            top_workouts = await session.execute(
                select(User.name, func.count(Workout.workout_id).label('total'))
                .join(Workout)
                .group_by(User.user_id)
                .order_by(func.count(Workout.workout_id).desc())
                .limit(5)
            )
            top_workouts = top_workouts.all()

            message = (
                "📊 Общая статистика:\n"
                f"👥 Всего пользователей: {stats['users_count']}\n"
                f"🏋️ Всего тренировок: {stats['workouts_count']}\n"
                f"⏱️ Общая длительность: {stats['total_duration']} мин\n"
                f"🔥 Сожжено калорий: {stats['total_calories']}\n\n"
                "🏆 Топ-5 пользователей:\n"
                "По длительности тренировок:\n"
            )

            for i, (name, total) in enumerate(top_duration, 1):
                message += f"{i}. {name}: {total} мин\n"

            message += "\nПо сожжённым калориям:\n"
            for i, (name, total) in enumerate(top_calories, 1):
                message += f"{i}. {name}: {total} кал\n"

            message += "\nПо количеству тренировок:\n"
            for i, (name, total) in enumerate(top_workouts, 1):
                message += f"{i}. {name}: {total}\n"

            await callback.message.edit_text(
                message,
                reply_markup=stats_back_kb()
            )
        except Exception as e:
            logging.error(f"Global stats error: {e}")


@router.callback_query(F.data == "stats_back")
async def handle_stats_back(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "📊 Выберите тип статистики:",
        reply_markup=stats_options_kb()
    )


@router.callback_query(F.data == "stats_export")
async def ask_export_format(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "Выберите формат экспорта данных:",
        reply_markup=export_format_kb()
    )
    await state.set_state(AdminStates.waiting_for_export_format)


@router.callback_query(F.data.startswith("export_"))
async def export_data(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    export_format = callback.data.split("_")[-1]

    async for session in get_db_session():
        try:
            admin = await get_user(session, callback.from_user.id)
            if not admin or not admin.is_admin:
                return await callback.answer("🚫 Доступ запрещён!", show_alert=True)

            workouts = await session.execute(
                select(Workout, User)
                .join(User)
                .order_by(Workout.date)
            )
            workouts = workouts.all()

            if not workouts:
                return await callback.answer("❌ Нет данных для экспорта", show_alert=True)

            if export_format == "csv":
                buf = io.StringIO()
                writer = csv.writer(buf, delimiter=';')
                writer.writerow(["ID", "User", "Date", "Type", "Duration", "Distance", "Calories", "Notes"])

                for workout, user in workouts:
                    writer.writerow([
                        workout.workout_id,
                        user.name,
                        workout.date.strftime('%Y-%m-%d %H:%M'),
                        workout.type,
                        workout.duration,
                        workout.distance,
                        workout.calories,
                        workout.notes or ""
                    ])

                buf.seek(0)
                csv_data = buf.getvalue().encode('utf-8-sig')
                file = BufferedInputFile(csv_data, filename="workouts_export.csv")

                await bot.send_document(
                    chat_id=callback.from_user.id,
                    document=file,
                    caption="📤 Экспорт данных в CSV"
                )

            elif export_format == "json":
                data = []
                for workout, user in workouts:
                    data.append({
                        "id": workout.workout_id,
                        "user": user.name,
                        "date": workout.date.strftime('%Y-%m-%d %H:%M'),
                        "type": workout.type,
                        "duration": workout.duration,
                        "distance": workout.distance,
                        "calories": workout.calories,
                        "notes": workout.notes
                    })

                json_data = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
                file = BufferedInputFile(json_data, filename="workouts_export.json")

                await bot.send_document(
                    chat_id=callback.from_user.id,
                    document=file,
                    caption="📤 Экспорт данных в JSON"
                )

            await callback.message.edit_text(
                "Экспорт завершен",
                reply_markup=stats_back_kb()
            )
        except Exception as e:
            logging.error(f"Export error: {e}")


@router.callback_query(F.data.startswith("admin_promote_"))
async def promote_user(callback: CallbackQuery):
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])

    async for session in get_db_session():
        try:
            admin = await get_user(session, callback.from_user.id)
            if not admin or not admin.is_admin:
                return await callback.answer("🚫 Доступ запрещён!", show_alert=True)

            user = await session.execute(
                select(User).where(User.telegram_id == user_id))
            user = user.scalars().first()

            if not user:
                return await callback.answer("❌ Пользователь не найден!", show_alert=True)

            user.is_admin = not user.is_admin
            await session.commit()

            action = "назначен админом" if user.is_admin else "снят с админки"
            await callback.message.edit_text(
                f"✅ Пользователь {user.name} {action}.",
                reply_markup=admin_back_kb()
            )
        except Exception as e:
            await session.rollback()
            logging.error(f"Promote error: {e}")


@router.callback_query(F.data.startswith("admin_message_"))
async def ask_message_to_user(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(target_user_id=user_id)
    await callback.message.edit_text(
        "Введите сообщение для пользователя:",
        reply_markup=admin_back_kb()
    )
    await state.set_state(AdminStates.waiting_for_user_message)


@router.message(AdminStates.waiting_for_user_message)
async def send_message_to_user(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = data.get("target_user_id")
    text = message.text

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"📨 Сообщение от администратора:\n{text}"
        )
        await message.answer(
            f"✅ Сообщение отправлено пользователю с ID {user_id}",
            reply_markup=admin_panel_kb()
        )
    except Exception as e:
        await message.answer(
            f"❌ Не удалось отправить сообщение: {str(e)}",
            reply_markup=admin_panel_kb()
        )
    await state.clear()


@router.callback_query(F.data.startswith("admin_user_stats_"))
async def show_user_stats(callback: CallbackQuery):
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])

    async for session in get_db_session():
        try:
            admin = await get_user(session, callback.from_user.id)
            if not admin or not admin.is_admin:
                return await callback.answer("🚫 Доступ запрещён!", show_alert=True)

            user = await session.execute(
                select(User).where(User.telegram_id == user_id))
            user = user.scalars().first()

            if not user:
                return await callback.answer("❌ Пользователь не найден!", show_alert=True)

            stats = await get_user_stats(session, user.user_id)

            top_workouts = await session.execute(
                select(Workout)
                .where(Workout.user_id == user.user_id)
                .order_by(Workout.duration.desc())
                .limit(5)
            )
            top_workouts = top_workouts.scalars().all()

            message = (
                f"📊 Статистика пользователя {user.name}:\n"
                f"Всего тренировок: {stats['workouts_count']}\n"
                f"Общая длительность: {stats['total_duration']} мин\n"
                f"Сожжено калорий: {stats['total_calories']}\n\n"
                "🏆 Топ-5 самых длительных тренировок:\n"
            )

            for i, workout in enumerate(top_workouts, 1):
                message += (
                    f"{i}. {workout.type} - {workout.duration} мин "
                    f"({workout.date.strftime('%d.%m.%Y')})\n"
                )

            await callback.message.edit_text(
                message,
                reply_markup=user_actions_kb(user.telegram_id, user.is_banned, user.is_admin)
            )
        except Exception as e:
            logging.error(f"User stats error: {e}")

@router.callback_query(F.data == "stats_graph")
async def generate_stats_graph(callback: CallbackQuery, bot: Bot):
    """Генерирует график статистики"""
    await callback.answer()
    async for session in get_db_session():
        try:
            admin = await get_user(session, callback.from_user.id)
            if not admin or not admin.is_admin:
                return await callback.answer("🚫 Доступ запрещён!", show_alert=True)

            workouts_by_date = await session.execute(
                select(
                    func.date(Workout.date).label('day'),
                    func.count(Workout.workout_id).label('count')
                )
                .group_by(func.date(Workout.date))
                .order_by(func.date(Workout.date))
            )
            workouts_by_date = workouts_by_date.all()

            if not workouts_by_date:
                return await callback.message.edit_text(
                    "❌ Нет данных для построения графика",
                    reply_markup=stats_back_kb()
                )

            plt.switch_backend('Agg')
            plt.figure(figsize=(10, 5))

            dates = [row.day for row in workouts_by_date]
            counts = [row.count for row in workouts_by_date]

            plt.plot(dates, counts, marker='o', linestyle='-')
            plt.title('Количество тренировок по дням')
            plt.xlabel('Дата')
            plt.ylabel('Количество тренировок')
            plt.xticks(rotation=45)
            plt.grid(True)
            plt.tight_layout()

            temp_file = io.BytesIO()
            plt.savefig(temp_file, format='png', dpi=80)
            temp_file.seek(0)
            plt.close()

            input_file = BufferedInputFile(temp_file.read(), filename="workouts_graph.png")

            # Отправляем график как новое сообщение
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=input_file,
                caption="📈 График количества тренировок по дням"
            )

            # Возвращаем пользователя в меню статистики
            await callback.message.edit_text(
                "График отправлен. Выберите следующее действие:",
                reply_markup=stats_back_kb()
            )

        except Exception as e:
            await callback.message.edit_text(
                "❌ Ошибка при генерации графика",
                reply_markup=stats_back_kb()
            )
            logging.error(f"Graph generation error: {e}", exc_info=True)

@router.callback_query(F.data == "admin_search_user")
async def ask_user_search(callback: CallbackQuery, state: FSMContext):
    """Запрашивает имя пользователя для поиска"""
    await callback.answer()
    await callback.message.edit_text(
        "Введите имя пользователя или его часть для поиска:",
        reply_markup=admin_back_kb()
    )
    await state.set_state(AdminStates.waiting_for_user_search)

@router.message(AdminStates.waiting_for_user_search)
async def process_user_search(message: Message, state: FSMContext):
    """Обрабатывает поиск пользователя"""
    search_term = message.text.strip()
    if search_term.startswith("@"):
        search_term = search_term[1:]

    async for session in get_db_session():
        try:
            admin = await get_user(session, message.from_user.id)
            if not admin or not admin.is_admin:
                return await message.answer("🚫 Доступ запрещён!")

            users = await session.execute(
                select(User)
                .where(User.name.ilike(f"%{search_term}%"))
                .limit(10)
            )
            users = users.scalars().all()

            if not users:
                return await message.answer(
                    f"❌ Пользователи по запросу '{search_term}' не найдены",
                    reply_markup=admin_back_kb()
                )

            builder = InlineKeyboardBuilder()
            for user in users:
                builder.row(
                    InlineKeyboardButton(
                        text=f"{user.name} (ID: {user.telegram_id})",
                        callback_data=f"user_select_{user.telegram_id}"
                    )
                )

            builder.row(
                InlineKeyboardButton(
                    text="⬅️ В админ-панель",
                    callback_data="admin_back"
                )
            )

            await message.answer(
                f"🔍 Результаты поиска по запросу '{search_term}':",
                reply_markup=builder.as_markup()
            )
            await state.clear()
        except Exception as e:
            await message.answer(
                "❌ Ошибка при поиске пользователя",
                reply_markup=admin_back_kb()
            )
            logging.error(f"User search error: {e}")


@router.callback_query(F.data.startswith("admin_ban_"))
async def ban_user_direct(callback: CallbackQuery):
    """Обрабатывает прямое нажатие кнопки бана из меню пользователя"""
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])

    async for session in get_db_session():
        try:
            admin = await get_user(session, callback.from_user.id)
            if not admin or not admin.is_admin:
                return await callback.answer("🚫 Доступ запрещён!", show_alert=True)

            user = await session.execute(
                select(User).where(User.telegram_id == user_id))
            user = user.scalars().first()

            if not user:
                return await callback.answer("❌ Пользователь не найден!", show_alert=True)

            await callback.message.edit_text(
                f"Вы действительно хотите {'разбанить' if user.is_banned else 'забанить'} пользователя {user.name}?",
                reply_markup=ban_confirm_kb(user.telegram_id, user.is_banned)
            )

        except Exception as e:
            await callback.message.edit_text(
                "❌ Ошибка при обработке запроса",
                reply_markup=admin_back_kb()
            )
            logging.error(f"Ban request error: {e}")