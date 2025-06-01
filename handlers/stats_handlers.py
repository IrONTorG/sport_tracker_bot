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
from ml.predictor import predict_future_workouts
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from datetime import timedelta
import numpy as np

router = Router()


@router.message(F.text == "📊 Моя статистика")
async def stats_menu(message: Message, state: FSMContext):
    """Меню выбора периода статистики"""
    # Сохраняем ID сообщения для последующего редактирования
    sent_message = await message.answer(
        "Выберите период для статистики:",
        reply_markup=get_stats_period_kb()
    )
    await state.update_data(stats_message_id=sent_message.message_id)


@router.callback_query(F.data.startswith("stats_"))
async def process_stats_period(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора периода статистики"""
    period = callback.data.split('_')[1]
    period_names = {
        "day": "день",
        "week": "неделю",
        "month": "месяц",
        "all": "всё время"
    }

    async for session in get_db_session():
        try:
            user_id = callback.from_user.id
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
                    Workout.user_id == user.user_id,
                    Workout.date >= start_date,
                    Workout.date <= end_date
                )
            )
            stats = stats.first()

            if not stats.workouts_count:
                response = f"📊 У вас нет тренировок за {period_names[period]}."
            else:
                response = (
                    f"📊 <b>Ваша статистика за {period_names[period]}:</b>\n\n"
                    f"🏋️‍♂️ <b>Количество тренировок:</b> {stats.workouts_count}\n"
                    f"⏱ <b>Общее время:</b> {stats.total_duration:.1f} мин.\n"
                    f"🔥 <b>Сожжено калорий:</b> {stats.total_calories:.0f} ккал\n"
                    f"📏 <b>Общая дистанция:</b> {stats.total_distance:.1f} км"
                )

            data = await state.get_data()
            message_id = data.get('stats_message_id', callback.message.message_id)

            try:
                await callback.message.bot.edit_message_text(
                    chat_id=callback.message.chat.id,
                    message_id=message_id,
                    text=response,
                    reply_markup=get_stats_period_kb()
                )
            except:
                # Если не удалось редактировать, отправляем новое сообщение
                sent_message = await callback.message.answer(
                    response,
                    reply_markup=get_stats_period_kb()
                )
                await state.update_data(stats_message_id=sent_message.message_id)

            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка получения статистики: {e}")
            await callback.message.answer("❌ Ошибка при получении статистики")


async def generate_workout_csv(workouts: list) -> io.BytesIO:
    """Генерация CSV файла с тренировками"""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    # Заголовки с единицами
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
        exercises = ", ".join([ex.name for ex in workout.exercises]) if workout.exercises else ""
        sets = reps = weight = ""

        if workout.exercises:
            first = workout.exercises[0]
            sets = str(first.sets) if first.sets else ""
            reps = str(first.reps) if first.reps else ""
            weight = f"{first.weight} кг" if first.weight else ""

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
            workout.notes or ""
        ])

    # Переводим в байты с BOM
    byte_stream = io.BytesIO()
    byte_stream.write(output.getvalue().encode('utf-8-sig'))
    byte_stream.seek(0)
    return byte_stream


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


async def generate_progress_chart(workouts: list) -> tuple[io.BytesIO, str]:
    """Генерация графика прогресса с ИИ-прогнозом"""
    if not workouts:
        return None, "Нет тренировок для анализа."

    dates = [w.date for w in workouts]
    calories = [w.calories for w in workouts]
    durations = [w.duration for w in workouts]

    # Переводим даты в числовую шкалу
    base_date = min(dates)
    x = np.array([(d - base_date).days for d in dates]).reshape(-1, 1)

    # Обучаем модели
    duration_model = LinearRegression().fit(x, durations)
    calorie_model = LinearRegression().fit(x, calories)

    # Прогноз на 5 дней вперёд
    steps = 5
    last_day = x[-1][0]
    future_x = np.array([last_day + i for i in range(1, steps + 1)]).reshape(-1, 1)
    future_dates = [base_date + timedelta(days=int(i[0])) for i in future_x]
    predicted_durations = duration_model.predict(future_x)
    predicted_calories = calorie_model.predict(future_x)
    predicted_durations = np.maximum(predicted_durations, 0)
    predicted_calories = np.maximum(predicted_calories, 0)

    # --- Рисуем график ---
    plt.figure(figsize=(10, 6))

    # Калории
    plt.subplot(2, 1, 1)
    plt.plot(dates, calories, 'r-', label='Факт')
    plt.plot(future_dates, predicted_calories, 'g--', label='Прогноз')
    plt.ylabel('Калории')
    plt.title('📈 Прогресс тренировок')
    plt.legend()
    plt.grid(True)

    # Длительность
    plt.subplot(2, 1, 2)



    
    plt.plot(dates, durations, 'b-', label='Факт')
    plt.plot(future_dates, predicted_durations, 'g--', label='Прогноз')
    plt.ylabel('Длительность (мин)')
    plt.xlabel('Дата')
    plt.legend()
    plt.grid(True)

    plt.tight_layout()

    # Сохраняем график
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    # Сообщение от ИИ
    message = "🤖 Прогноз на ближайшие 5 тренировок:\n"
    for date, dur, cal in zip(future_dates, predicted_durations, predicted_calories):
        message += f"📅 {date.strftime('%d.%m')} — {round(dur, 1)} мин, {round(cal, 1)} ккал\n"

    return buf, message


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
    """Показать график прогресса + ИИ-прогноз"""
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
            workouts = result.scalars().all()

            if not workouts:
                await callback.answer("Нет данных для построения графика")
                return

            chart, ai_message = await generate_progress_chart(workouts)

            await callback.message.answer_photo(
                BufferedInputFile(
                    chart.getvalue(),
                    filename="progress_chart.png"
                ),
                caption=ai_message
            )
            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка построения графика: {e}")
            await callback.answer("❌ Ошибка при построении графика")