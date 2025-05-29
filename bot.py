import logging
import asyncio


from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand
from config import Config
from database.session import engine, Base, check_db_connection, get_db_session
from database.models import Reminder, User  # Добавлен импорт Reminder
from handlers import user_handlers, admin_handlers, workout_handlers, reminder_handlers, stats_handlers
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, time
import pytz
from sqlalchemy import select, func
import os


async def send_reminders(bot: Bot):
    tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(tz)
    current_time = now.time().replace(second=0, microsecond=0)
    current_day = now.strftime("%A")

    day_mapping = {
        "Monday": "понедельник",
        "Tuesday": "вторник",
        "Wednesday": "среда",
        "Thursday": "четверг",
        "Friday": "пятница",
        "Saturday": "суббота",
        "Sunday": "воскресенье"
    }
    current_day_ru = day_mapping.get(current_day, current_day)

    logging.info(f"Проверка напоминаний в {current_time} ({current_day}/{current_day_ru})")

    try:
        async for session in get_db_session():
            # Ищем напоминания для текущего времени и дня
            stmt = select(Reminder).join(User).where(
                (Reminder.day_of_week == current_day) | (Reminder.day_of_week == current_day_ru),
                func.time(Reminder.reminder_time) == current_time,
                User.is_banned == False
            )

            result = await session.execute(stmt)
            reminders = result.scalars().all()

            # Предварительно загружаем связанные объекты User
            for reminder in reminders:
                await session.refresh(reminder, ['user'])  # Явно загружаем отношение

            for reminder in reminders:
                try:
                    if reminder.user:  # Теперь user должен быть доступен
                        await bot.send_message(
                            chat_id=reminder.user.telegram_id,
                            text=f"🔔 Напоминание:\n{reminder.reminder_text}"
                        )
                        logging.info(f"Напоминание отправлено пользователю {reminder.user.telegram_id}")
                except Exception as e:
                    logging.error(f"Ошибка отправки напоминания: {str(e)}", exc_info=True)
    except Exception as e:
        logging.error(f"Ошибка при проверке напоминаний: {str(e)}", exc_info=True)




async def on_startup(bot: Bot):


    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Настройка планировщика для напоминаний
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    scheduler.add_job(
        send_reminders,
        'interval',
        seconds=10,  # Для теста
        args=[bot],
        next_run_time=datetime.now()
    )

    scheduler.start()

    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="add", description="Добавить тренировку"),
        BotCommand(command="remind", description="Управление напоминаниями"),
        BotCommand(command="admin", description="Админ-панель (для админов)")
    ])
    logging.info("✅ Бот успешно запущен")


async def on_shutdown(dp: Dispatcher):
    """Действия при выключении бота"""
    logging.warning("🛑 Выключаемся...")
    await dp.storage.close()
    await dp.fsm.storage.close()
    await engine.dispose()


async def main():
    """Основная функция запуска бота"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация обработчиков
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(workout_handlers.router)
    dp.include_router(reminder_handlers.router)
    dp.include_router(stats_handlers.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())