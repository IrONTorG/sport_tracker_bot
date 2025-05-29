import logging
from datetime import datetime, time, timedelta

from typing import Union
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete
from database.session import get_db_session
from database.models import Reminder, User
from states import ReminderStates
from sqlalchemy import update
import pytz
from keyboards.main_menu import get_main_menu
from keyboards.reminder import (
    get_weekdays_kb,
    reminders_control_kb,
    edit_reminder_kb,
    common_times_kb
)

router = Router()

WEEKDAYS = {
    "понедельник": "Monday",
    "вторник": "Tuesday",
    "среда": "Wednesday",
    "четверг": "Thursday",
    "пятница": "Friday",
    "суббота": "Saturday",
    "воскресенье": "Sunday"
}


@router.message(F.text == "🔔 Напоминания")
@router.message(Command("remind"))
async def handle_reminders_command(message: Message):
    """Главное меню напоминаний"""
    await message.answer(
        "Управление напоминаниями:",
        reply_markup=reminders_control_kb([])  # Пустой список, так как кнопки фиксированные
    )

@router.callback_query(F.data.startswith("rem_view_"))
async def view_reminder(callback: CallbackQuery):
    """Просмотр конкретного напоминания"""
    try:
        reminder_id = int(callback.data.split('_')[2])
        async for session in get_db_session():
            reminder = await session.execute(
                select(Reminder).where(Reminder.reminder_id == reminder_id)
            )
            reminder = reminder.scalar_one_or_none()

            if not reminder:
                await callback.answer("Напоминание не найдено")
                return

            await callback.message.edit_text(
                f"📅 День: {reminder.day_of_week}\n"
                f"⏰ Время: {reminder.reminder_time.strftime('%H:%M')}\n"
                f"📝 Текст: {reminder.reminder_text}",
                reply_markup=edit_reminder_kb(reminder_id)
            )
            await callback.answer()
    except Exception as e:
        logging.error(f"Ошибка просмотра напоминания: {e}")
        await callback.answer("❌ Ошибка при просмотре напоминания")

@router.callback_query(F.data == "rem_delete_all")
async def delete_all_reminders(callback: CallbackQuery):
    """Удаление всех напоминаний пользователя"""
    try:
        async for session in get_db_session():
            # Получаем пользователя
            user = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            user = user.scalar_one_or_none()

            if not user:
                await callback.answer("Пользователь не найден")
                return

            # Удаляем все напоминания
            await session.execute(
                delete(Reminder).where(Reminder.user_id == user.user_id)
            )
            await session.commit()

            await callback.message.answer("✅ Все напоминания удалены")
    except Exception as e:
        await session.rollback()
        logging.error(f"Ошибка удаления всех напоминаний: {e}")
        await callback.message.answer("❌ Не удалось удалить напоминания")
    finally:
        await callback.answer()

@router.message(F.text == "🔔 Мои напоминания")
async def handle_my_reminders_command(message: Message):
    """Обработка кнопки из главного меню"""
    await show_user_reminders(message)

async def show_user_reminders(event: Union[Message, CallbackQuery]):
    """Общая функция для показа напоминаний"""
    try:
        async for session in get_db_session():
            # Получаем пользователя
            user = await session.execute(
                select(User).where(User.telegram_id == event.from_user.id)
            )
            user = user.scalar_one_or_none()

            if not user:
                response = "Пользователь не найден"
                if isinstance(event, CallbackQuery):
                    await event.answer(response)
                else:
                    await event.answer(response)
                return

            # Получаем напоминания
            reminders = await session.execute(
                select(Reminder).where(Reminder.user_id == user.user_id)
            )
            reminders = reminders.scalars().all()

            if not reminders:
                response = "У вас нет напоминаний."
                if isinstance(event, CallbackQuery):
                    await event.message.answer(response)
                    await event.answer()  # Подтверждаем обработку callback
                else:
                    await event.answer(response)
                return

            # Формируем список
            reminders_list = []
            for rem in reminders:
                reminders_list.append({
                    'id': rem.reminder_id,
                    'day': rem.day_of_week,
                    'time': rem.reminder_time.strftime("%H:%M"),
                    'text': rem.reminder_text[:30] + "..." if len(rem.reminder_text) > 30 else rem.reminder_text
                })

            # Отправляем сообщение
            response = "Ваши напоминания:"
            if isinstance(event, CallbackQuery):
                try:
                    await event.message.edit_text(
                        response,
                        reply_markup=reminders_control_kb(reminders_list)
                    )
                except Exception as e:
                    await event.message.answer(
                        response,
                        reply_markup=reminders_control_kb(reminders_list)
                    )
                await event.answer()  # Всегда отвечаем на callback
            else:
                await event.answer(
                    response,
                    reply_markup=reminders_control_kb(reminders_list)
                )
    except Exception as e:
        logging.error(f"Ошибка получения напоминаний: {e}")
        response = "❌ Ошибка при получении напоминаний"
        if isinstance(event, CallbackQuery):
            await event.message.answer(response)
            await event.answer()
        else:
            await event.answer(response)


@router.callback_query(F.data == "rem_create_new")
async def create_new_reminder(callback: CallbackQuery, state: FSMContext):
    """Начало создания нового напоминания"""
    await callback.message.answer(
        "Выберите день недели для напоминания:",
        reply_markup=get_weekdays_kb()
    )
    await state.set_state(ReminderStates.waiting_for_day)
    await callback.answer()


@router.message(ReminderStates.waiting_for_day)
async def process_day_selection(message: Message, state: FSMContext):
    """Обработка выбора дня недели"""
    day = message.text.strip().lower()
    if day not in WEEKDAYS:
        await message.answer(
            "Пожалуйста, выберите день из предложенных вариантов:",
            reply_markup=get_weekdays_kb()
        )
        return

    await state.update_data(day=WEEKDAYS[day])
    await message.answer(
        "Выберите время или введите в формате ЧЧ:ММ:",
        reply_markup=common_times_kb()
    )
    await state.set_state(ReminderStates.waiting_for_time)


@router.message(ReminderStates.waiting_for_time)
async def process_time_input(message: Message, state: FSMContext):
    """Валидация и обработка времени"""
    try:
        time_str = message.text.strip()
        hours, minutes = map(int, time_str.split(':'))
        if not (0 <= hours < 24 and 0 <= minutes < 60):
            raise ValueError

        # Сохраняем как строку "HH:MM:SS"
        await state.update_data(time=f"{hours:02d}:{minutes:02d}:00")
        await state.set_state(ReminderStates.waiting_for_text)
        await message.answer(
            "Введите текст напоминания:",
            reply_markup=ReplyKeyboardRemove()
        )
    except (ValueError, AttributeError):
        await message.answer(
            "Некорректный формат времени. Пожалуйста, введите время как ЧЧ:ММ\n"
            "Пример: 07:30 или 19:45",
            reply_markup=common_times_kb()
        )


@router.message(ReminderStates.waiting_for_text)
async def process_reminder_text(message: Message, state: FSMContext):
    data = await state.get_data()
    time_str = data['time']  # "HH:MM:SS"

    try:
        # Создаем объект time без микросекунд
        h, m, s = map(int, time_str.split(':'))
        reminder_time = time(hour=h, minute=m, second=s)

        async for session in get_db_session():
            # Явно указываем тип при создании объекта
            reminder = Reminder(
                user_id=(await session.execute(
                    select(User.user_id).where(User.telegram_id == message.from_user.id)
                )).scalar_one(),
                reminder_text=message.text,
                reminder_time=reminder_time,
                day_of_week=data['day']
            )

            session.add(reminder)
            await session.commit()

            await message.answer(
                f"✅ Напоминание создано на {time_str[:8]}",
                parse_mode=None
            )
    except Exception as e:
        logging.error(f"Ошибка сохранения: {str(e)}", exc_info=True)
        await message.answer("❌ Ошибка при создании напоминания")
    finally:
        await state.clear()


@router.callback_query(F.data == "rem_my_reminders")
async def handle_my_reminders_callback(callback: CallbackQuery):
    """Обработка callback кнопки"""
    await show_user_reminders(callback)
    try:
        async for session in get_db_session():
            user = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            user = user.scalar_one_or_none()

            if not user:
                await callback.answer("Пользователь не найден")
                return

            reminders = await session.execute(
                select(Reminder).where(Reminder.user_id == user.user_id)
            )
            reminders = reminders.scalars().all()

            if not reminders:
                await callback.message.answer("У вас нет напоминаний.")
                await callback.answer()
                return

            reminders_list = []
            for rem in reminders:
                reminders_list.append({
                    'id': rem.reminder_id,
                    'day': rem.day_of_week,
                    'time': rem.reminder_time.strftime("%H:%M"),
                    'text': rem.reminder_text[:30] + "..." if len(rem.reminder_text) > 30 else rem.reminder_text
                })

            await callback.message.edit_text(
                "Ваши напоминания:",
                reply_markup=reminders_control_kb(reminders_list)
            )
    except Exception as e:
        logging.error(f"Ошибка получения напоминаний: {e}")
        await callback.answer("❌ Ошибка при получении напоминаний")
    finally:
        await callback.answer()

@router.callback_query(F.data.startswith("rem_edit_text_"))
async def edit_reminder_text(callback: CallbackQuery, state: FSMContext):
    """Редактирование текста напоминания"""
    reminder_id = int(callback.data.split('_')[3])
    await state.update_data(reminder_id=reminder_id)
    await state.set_state(ReminderStates.editing_text)
    await callback.message.answer("Введите новый текст напоминания:")
    await callback.answer()

@router.message(ReminderStates.editing_text)
async def process_edit_text(message: Message, state: FSMContext):
    """Обработка нового текста"""
    data = await state.get_data()
    async for session in get_db_session():
        try:
            await session.execute(
                update(Reminder)
                .where(Reminder.reminder_id == data['reminder_id'])
                .values(reminder_text=message.text)
            )
            await session.commit()
            await message.answer("✅ Текст напоминания обновлён")
        except Exception as e:
            await session.rollback()
            logging.error(f"Ошибка обновления текста: {e}")
            await message.answer("❌ Не удалось обновить текст")
        finally:
            await state.clear()


@router.callback_query(F.data.startswith("rem_delete_"))
async def delete_reminder(callback: CallbackQuery):
    """Удаление напоминания"""
    reminder_id = int(callback.data.split('_')[2])
    async for session in get_db_session():
        try:
            await session.execute(
                delete(Reminder).where(Reminder.reminder_id == reminder_id))
            await session.commit()
            await callback.message.answer("✅ Напоминание удалено")
        except Exception as e:
            await session.rollback()
            logging.error(f"Ошибка удаления напоминания: {e}")
            await callback.message.answer("❌ Не удалось удалить напоминание")
        finally:
            await callback.answer()


@router.message(Command("test_reminder"))
async def test_reminder(message: Message):
    """Тестовая команда для проверки отправки напоминания"""
    try:
        # Создаем тестовое напоминание на текущее время + 1 минута
        test_time = (datetime.now() + timedelta(minutes=1)).time()

        async for session in get_db_session():
            user = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = user.scalar_one()

            reminder = Reminder(
                user_id=user.user_id,
                reminder_text="🔴 ЭТО ТЕСТОВОЕ НАПОМИНАНИЕ!",
                reminder_time=datetime.combine(datetime.today(), test_time),
                day_of_week=datetime.now().strftime("%A")
            )

            session.add(reminder)
            await session.commit()

            await message.answer(
                f"⏰ Тестовое напоминание создано!\n"
                f"Оно придет в {test_time.strftime('%H:%M')}\n"
                f"Текущее время: {datetime.now().strftime('%H:%M')}"
            )
    except Exception as e:
        logging.error(f"Ошибка создания тестового напоминания: {e}")
        await message.answer("❌ Не удалось создать тестовое напоминание")

@router.message(Command("time"))
async def check_time(message: Message):
    tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(tz)
    await message.answer(
        f"Текущее время сервера:\n"
        f"{now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"День недели: {now.strftime('%A')}"
    )

@router.message(Command("force_reminder"))
async def force_reminder(message: Message):
    """Принудительно отправить тестовое напоминание"""
    try:
        await message.answer("🔔 ТЕСТОВОЕ НАПОМИНАНИЕ!")
        logging.info("Тестовое напоминание отправлено вручную")
    except Exception as e:
        logging.error(f"Ошибка отправки тестового напоминания: {e}")

@router.message(Command("test_time"))
async def test_time_format(message: Message):
    test_time = time(hour=12, minute=30, second=0)
    await message.answer(
        f"Тестовое время: {test_time}\n"
        f"Тип: {type(test_time)}\n"
        f"В БД будет сохранено как: {test_time.strftime('%H:%M:%S')}",
        parse_mode=None  # Отключаем разметку
    )

@router.message(Command("check_reminders"))
async def check_reminders(message: Message):
    async for session in get_db_session():
        reminders = await session.execute(select(Reminder))
        for rem in reminders.scalars():
            await message.answer(
                f"ID: {rem.reminder_id}\n"
                f"Время: {rem.reminder_time}\n"
                f"Тип: {type(rem.reminder_time)}",
                parse_mode=None
            )