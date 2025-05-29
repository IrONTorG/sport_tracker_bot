from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from sqlalchemy import select, func
from database.session import get_db_session
from database.models import Workout, User  # Added User import
from keyboards.stats import get_stats_period_kb
import logging
from sqlalchemy.orm import joinedload
from aiogram.types import BufferedInputFile
import csv
import json
import io
import matplotlib.pyplot as plt

router = Router()


@router.message(F.text == "📊 Моя статистика")
async def stats_menu(message: Message):
    """Меню выбора периода статистики"""
    await message.answer(
        "Выберите период для статистики:",
        reply_markup=get_stats_period_kb()
    )


@router.callback_query(F.data.startswith("stats_"))
async def process_stats_period(callback: CallbackQuery):
    """Обработка выбора периода статистики"""
    period = callback.data.split('_')[1]
    async for session in get_db_session():
        try:
            user_id = callback.from_user.id

            # Get user from database first
            user = await session.execute(
                select(User).where(User.telegram_id == user_id))
            user = user.scalar_one_or_none()

            if not user:
                await callback.message.answer("Пользователь не найден")
                return

            # Определяем временной диапазон
            end_date = datetime.now()
            if period == "day":
                start_date = end_date - timedelta(days=1)
            elif period == "week":
                start_date = end_date - timedelta(weeks=1)
            elif period == "month":
                start_date = end_date - timedelta(days=30)
            else:
                start_date = datetime.min  # Для "все время"

            # Получаем статистику
            stats = await session.execute(
                select(
                    func.count(Workout.workout_id).label("workouts_count"),
                    func.coalesce(func.sum(Workout.duration), 0).label("total_duration"),
                    func.coalesce(func.sum(Workout.calories), 0).label("total_calories"),
                    func.coalesce(func.sum(Workout.distance), 0).label("total_distance")
                ).where(
                    Workout.user_id == user.user_id,  # Use database user_id
                    Workout.date >= start_date,
                    Workout.date <= end_date
                )
            )
            stats = stats.first()

            if not stats.workouts_count:
                await callback.message.answer("Нет данных за выбранный период")
                return

            # Формируем сообщение
            message_text = (
                f"📊 Статистика за {period}:\n"
                f"• Количество тренировок: {stats.workouts_count}\n"
                f"• Общее время: {stats.total_duration:.1f} мин.\n"
                f"• Сожжено калорий: {stats.total_calories:.0f} ккал\n"
                f"• Общая дистанция: {stats.total_distance:.1f} км"
            )

            await callback.message.answer(message_text)
        except Exception as e:
            logging.error(f"Ошибка получения статистики: {e}")
            await callback.message.answer("❌ Ошибка при получении статистики")
        finally:
            await callback.answer()


async def generate_workout_csv(workouts: list) -> io.StringIO:
    """Генерация CSV файла с тренировками"""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=',')  # Явно указываем разделитель

    # Заголовки с единицами измерения
    writer.writerow([
        "Дата",
        "Тип тренировки",
        "Длительность (мин)",
        "Сожжено калорий (ккал)",
        "Дистанция (км)",
        "Упражнения",
        "Подходы",
        "Повторения",
        "Вес (кг)",
        "Заметки"
    ])

    for workout in workouts:
        # Обработка упражнений для силовых тренировок
        exercises = ""
        sets = ""
        reps = ""
        weight = ""

        if workout.exercises:
            exercises = ", ".join([ex.name for ex in workout.exercises])
            if workout.type == "strength" and workout.exercises:
                sets = f"{workout.exercises[0].sets}"
                reps = f"{workout.exercises[0].reps}"
                weight = f"{workout.exercises[0].weight} кг" if workout.exercises[0].weight else ""

        # Форматирование данных с единицами измерения
        writer.writerow([
            workout.date.strftime("%Y-%m-%d %H:%M"),
            workout.type,
            f"{workout.duration} мин" if workout.duration else "",
            f"{workout.calories} ккал" if workout.calories else "",
            f"{workout.distance} км" if workout.distance else "",
            exercises,
            sets,
            reps,
            weight,
            workout.notes if workout.notes else ""
        ])

    output.seek(0)
    return output


async def generate_workout_json(workouts: list) -> str:
    """Генерация JSON файла с тренировками"""
    result = []

    for workout in workouts:
        workout_data = {
            "date": workout.date.strftime("%Y-%m-%d %H:%M"),
            "type": workout.type,
            "duration": workout.duration,
            "calories": workout.calories,
            "distance": workout.distance,
            "notes": workout.notes,
            "exercises": []
        }

        for exercise in workout.exercises:
            workout_data["exercises"].append({
                "name": exercise.name,
                "sets": exercise.sets,
                "reps": exercise.reps,
                "weight": exercise.weight
            })

        result.append(workout_data)

    return json.dumps(result, indent=2, ensure_ascii=False)


async def generate_progress_chart(workouts: list) -> io.BytesIO:
    """Генерация графика прогресса"""
    dates = []
    calories = []
    durations = []

    for workout in workouts:
        dates.append(workout.date)
        calories.append(workout.calories)
        durations.append(workout.duration)

    plt.figure(figsize=(10, 6))

    # График калорий
    plt.subplot(2, 1, 1)
    plt.plot(dates, calories, 'r-', label='Калории')
    plt.ylabel('Калории')
    plt.title('Прогресс тренировок')
    plt.grid(True)

    # График продолжительности
    plt.subplot(2, 1, 2)
    plt.plot(dates, durations, 'b-', label='Длительность (мин)')
    plt.ylabel('Длительность (мин)')
    plt.xlabel('Дата')
    plt.grid(True)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    return buf


@router.callback_query(F.data.startswith("export_"))
async def export_workouts(callback: CallbackQuery):
    """Экспорт тренировок в CSV или JSON"""
    format_type = callback.data.split('_')[1]

    async for session in get_db_session():
        try:
            user = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id))
            user = user.scalar_one()

            result = await session.execute(
                select(Workout)
                .where(Workout.user_id == user.user_id)
                .order_by(Workout.date)
                .options(joinedload(Workout.exercises))
            )
            workouts = result.unique().scalars().all()

            if not workouts:
                await callback.answer("Нет данных для экспорта")
                return

            if format_type == "csv":
                csv_file = await generate_workout_csv(workouts)
                await callback.message.answer_document(
                    BufferedInputFile(
                        csv_file.getvalue().encode('utf-8-sig'),  # Используем utf-8-sig для Excel
                        filename=f"workouts_{user.user_id}.csv"
                    ),
                    caption="Ваши тренировки в формате CSV"
                )
            elif format_type == "json":
                json_data = await generate_workout_json(workouts)
                await callback.message.answer_document(
                    BufferedInputFile(
                        json_data.encode('utf-8'),
                        filename=f"workouts_{user.user_id}.json"
                    ),
                    caption="Ваши тренировки в формате JSON"
                )

            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка экспорта: {e}")
            await callback.answer("❌ Ошибка при экспорте данных")


async def generate_workout_csv(workouts: list) -> io.StringIO:
    """Генерация CSV файла с тренировками"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Заголовки с правильной кодировкой
    writer.writerow([
        "Дата", "Тип тренировки", "Длительность (мин)",
        "Калории", "Дистанция (км)", "Упражнения", "Подходы",
        "Повторения", "Вес (кг)", "Заметки"
    ])

    for workout in workouts:
        exercises = ", ".join([ex.name for ex in workout.exercises]) if workout.exercises else ""
        sets = workout.exercises[0].sets if workout.exercises else ""
        reps = workout.exercises[0].reps if workout.exercises else ""
        weight = workout.exercises[0].weight if workout.exercises else ""

        writer.writerow([
            workout.date.strftime("%Y-%m-%d %H:%M"),
            workout.type,
            workout.duration,
            workout.calories,
            workout.distance if workout.distance else "",
            exercises,
            sets,
            reps,
            weight,
            workout.notes if workout.notes else ""
        ])

    output.seek(0)
    return output

@router.callback_query(F.data == "show_progress")
async def show_progress(callback: CallbackQuery):
    """Показать график прогресса"""
    async for session in get_db_session():
        try:
            user = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id))
            user = user.scalar_one()

            result = await session.execute(
                select(Workout)
                .where(Workout.user_id == user.user_id)
                .order_by(Workout.date)
            )
            workouts = result.scalars().all()  # Для графика не нужно joinedload

            if not workouts:
                await callback.answer("Нет данных для построения графика")
                return

            chart = await generate_progress_chart(workouts)
            await callback.message.answer_photo(
                BufferedInputFile(
                    chart.getvalue(),
                    filename="progress_chart.png"
                ),
                caption="Ваш прогресс по тренировкам"
            )
            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка построения графика: {e}")
            await callback.answer("❌ Ошибка при построении графика")