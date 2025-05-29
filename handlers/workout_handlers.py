import logging
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, KeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from datetime import datetime
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy import select, func, desc, delete
from database.session import get_db_session
from database.models import Workout, Exercise, User
from states import WorkoutStates, EditExerciseStates, EditWorkoutStates, DeleteWorkoutStates
from keyboards.main_menu import get_main_menu, get_workout_pagination_kb
from keyboards.workout_types import get_workout_types
from typing import Dict
from aiogram.fsm.state import State, StatesGroup


class PaginationStates(StatesGroup):
    viewing_workouts = State()


router = Router()

# Типы тренировок
WORKOUT_TYPES = {
    "🏋️‍ Силовая": "strength",
    "🏃 Бег": "running",
    "🚴 Велосипед": "cycling",
    "🧘 Йога": "yoga",
    "🏊 Плавание": "swimming",
    "🤸 Прыжки на скакалке": "jumping_rope"
}

DISTANCE_WORKOUTS = {"running", "cycling", "swimming"}


def format_exercise_details(exercise: Exercise) -> str:
    """Форматирует детали упражнения в строку"""
    return (
        f"Название: {exercise.name}\n"
        f"Подходы: {exercise.sets}\n"
        f"Повторения: {exercise.reps}\n"
        f"Вес: {exercise.weight} кг"
    )


@router.message(Command("add"))
@router.message(F.text == "➕ Добавить тренировку")
async def start_add_workout(message: Message, state: FSMContext):
    """Начало процесса добавления тренировки"""
    await message.answer(
        "Выберите тип тренировки:",
        reply_markup=get_workout_types()
    )
    await state.set_state(WorkoutStates.waiting_for_type)


@router.message(F.text == "📋 Мои тренировки")
async def show_workouts(message: Message, state: FSMContext):
    """Показывает первые 5 тренировок пользователя"""
    async for session in get_db_session():
        user = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id))
        user = user.scalar_one()

        workouts = await session.execute(
            select(Workout)
            .where(Workout.user_id == user.user_id)
            .order_by(desc(Workout.date))
            .limit(5)
        )
        workouts = workouts.scalars().all()

        if not workouts:
            await message.answer("У вас пока нет тренировок.", reply_markup=get_main_menu(user.is_admin))
            return

        total = await session.execute(
            select(func.count()).select_from(Workout).where(Workout.user_id == user.user_id))
        total = total.scalar()

        await state.update_data(
            current_page=1,
            total_pages=max(1, (total + 4) // 5),
            user_id=user.user_id
        )
        await state.set_state(PaginationStates.viewing_workouts)

        response = await format_workouts_response(workouts, 1, total, session)
        await message.answer(
            response,
            reply_markup=get_workout_pagination_kb(has_prev=False, has_next=total > 5)
        )


async def format_workouts_response(workouts: list, current_page: int, total: int, session) -> str:
    """Форматирует список тренировок в текст сообщения"""
    response = f"Ваши тренировки (страница {current_page}):\n\n"
    for i, workout in enumerate(workouts, 1):
        response += (
            f"{i}. {workout.type.capitalize()} - "
            f"{workout.date.strftime('%d.%m.%Y %H:%M')}\n"
            f"Длительность: {workout.duration} мин.\n"
        )

        if workout.distance:
            response += f"Дистанция: {workout.distance} км\n"

        if workout.type == "strength":
            exercises = await session.execute(
                select(Exercise).where(Exercise.workout_id == workout.workout_id))
            exercises = exercises.scalars().all()
            for ex in exercises:
                response += f"Упражнение: {ex.name} ({ex.sets}x{ex.reps} по {ex.weight}кг)\n"

        response += f"Калории: {workout.calories} ккал\n\n"

    response += f"Всего тренировок: {total}"
    return response


@router.message(PaginationStates.viewing_workouts, F.text.in_(["⬅️ Назад", "➡️ Вперед"]))
async def paginate_workouts(message: Message, state: FSMContext):
    """Обработка пагинации тренировок"""
    data = await state.get_data()
    current_page = data['current_page']
    total_pages = data['total_pages']
    user_id = data['user_id']

    if message.text == "⬅️ Назад" and current_page > 1:
        current_page -= 1
    elif message.text == "➡️ Вперед" and current_page < total_pages:
        current_page += 1
    else:
        await message.answer("Это крайняя страница.")
        return

    async for session in get_db_session():
        workouts = await session.execute(
            select(Workout)
            .where(Workout.user_id == user_id)
            .order_by(desc(Workout.date))
            .offset((current_page - 1) * 5)
            .limit(5)
        )
        workouts = workouts.scalars().all()

        total = await session.execute(
            select(func.count()).select_from(Workout).where(Workout.user_id == user_id))
        total = total.scalar()

        await state.update_data(current_page=current_page)

        response = await format_workouts_response(workouts, current_page, total, session)
        await message.answer(
            response,
            reply_markup=get_workout_pagination_kb(
                has_prev=current_page > 1,
                has_next=current_page < total_pages
            )
        )


@router.message(PaginationStates.viewing_workouts, F.text == "➕ Добавить тренировку")
async def add_workout_from_pagination(message: Message, state: FSMContext):
    """Переход к добавлению тренировки из режима просмотра"""
    await state.clear()
    await start_add_workout(message, state)


@router.message(PaginationStates.viewing_workouts, F.text == "🔙 Главное меню")
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


@router.message(WorkoutStates.waiting_for_type, F.text.in_(WORKOUT_TYPES.keys()))
async def process_workout_type(message: Message, state: FSMContext):
    """Обработка типа тренировки"""
    workout_type = WORKOUT_TYPES[message.text]
    await state.update_data(workout_type=workout_type)

    if workout_type == "strength":
        await message.answer(
            "Введите название упражнения:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(WorkoutStates.waiting_for_exercise_name)
    else:
        if workout_type in DISTANCE_WORKOUTS:
            await message.answer(
                "Введите дистанцию в км:",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.set_state(WorkoutStates.waiting_for_distance)
        else:
            await message.answer(
                "Введите продолжительность в минутах:",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.set_state(WorkoutStates.waiting_for_duration)


@router.message(WorkoutStates.waiting_for_exercise_name)
async def process_exercise_name(message: Message, state: FSMContext):
    """Обработка названия упражнения"""
    await state.update_data(exercise_name=message.text)
    await message.answer("Введите количество подходов:")
    await state.set_state(WorkoutStates.waiting_for_sets)


@router.message(WorkoutStates.waiting_for_sets)
async def process_sets(message: Message, state: FSMContext):
    """Обработка количества подходов"""
    try:
        sets = int(message.text)
        if sets <= 0:
            raise ValueError
        await state.update_data(sets=sets)
        await message.answer("Введите количество повторений:")
        await state.set_state(WorkoutStates.waiting_for_reps)
    except ValueError:
        await message.answer("Введите целое число больше 0")


@router.message(WorkoutStates.waiting_for_reps)
async def process_reps(message: Message, state: FSMContext):
    """Обработка количества повторений"""
    try:
        reps = int(message.text)
        if reps <= 0:
            raise ValueError
        await state.update_data(reps=reps)
        await message.answer("Введите вес (кг):")
        await state.set_state(WorkoutStates.waiting_for_weight)
    except ValueError:
        await message.answer("Введите целое число больше 0")


@router.message(WorkoutStates.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обработка веса и предложение добавить еще упражнение"""
    try:
        weight = int(message.text)
        if weight < 0:
            raise ValueError

        data = await state.get_data()
        current_exercises = data.get('exercises', [])

        current_exercises.append({
            'name': data['exercise_name'],
            'sets': data['sets'],
            'reps': data['reps'],
            'weight': weight
        })

        await state.update_data(exercises=current_exercises)

        builder = ReplyKeyboardBuilder()
        builder.row(KeyboardButton(text="✅ Завершить тренировку"))
        builder.row(KeyboardButton(text="➕ Добавить еще упражнение"))

        await message.answer(
            "Упражнение добавлено. Хотите добавить еще одно упражнение или завершить тренировку?",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
        await state.set_state(WorkoutStates.waiting_for_more_exercises)

    except ValueError:
        await message.answer("Введите число больше или равно 0")

@router.message(WorkoutStates.waiting_for_more_exercises, F.text == "➕ Добавить еще упражнение")
async def add_another_exercise(message: Message, state: FSMContext):
    """Начало добавления нового упражнения"""
    await message.answer(
        "Введите название следующего упражнения:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(WorkoutStates.waiting_for_exercise_name)

@router.message(WorkoutStates.waiting_for_more_exercises, F.text == "✅ Завершить тренировку")
async def finish_strength_workout(message: Message, state: FSMContext):
    """Завершение силовой тренировки и запрос продолжительности"""
    await message.answer(
        "Введите продолжительность тренировки в минутах:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(WorkoutStates.waiting_for_duration)


@router.message(WorkoutStates.waiting_for_duration)
async def process_duration(message: Message, state: FSMContext):
    """Обработка продолжительности"""
    try:
        duration = float(message.text)
        if duration <= 0:
            raise ValueError

        await state.update_data(duration=duration)
        await message.answer("Введите количество сожженных калорий:")
        await state.set_state(WorkoutStates.waiting_for_calories)
    except ValueError:
        await message.answer("Введите число больше 0")


@router.message(WorkoutStates.waiting_for_distance)
async def process_distance(message: Message, state: FSMContext):
    """Обработка дистанции"""
    try:
        distance = float(message.text)
        if distance <= 0:
            raise ValueError

        await state.update_data(distance=distance)
        await message.answer("Введите продолжительность в минутах:")
        await state.set_state(WorkoutStates.waiting_for_duration)
    except ValueError:
        await message.answer("Введите число больше 0")


@router.message(WorkoutStates.waiting_for_calories)
async def process_calories(message: Message, state: FSMContext):
    """Обработка калорий"""
    try:
        calories = float(message.text)
        if calories <= 0:
            raise ValueError

        await state.update_data(calories=calories)
        await message.answer("Введите заметки (или 'нет'):")
        await state.set_state(WorkoutStates.waiting_for_notes)
    except ValueError:
        await message.answer("Введите число больше 0")


@router.message(WorkoutStates.waiting_for_notes)
async def process_notes(message: Message, state: FSMContext):
    """Финальное сохранение тренировки"""
    data = await state.get_data()
    async for session in get_db_session():
        try:
            user = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id))
            user = user.scalar_one()

            workout = Workout(
                user_id=user.user_id,
                date=datetime.now(),
                type=data['workout_type'],
                duration=data['duration'],
                distance=data.get('distance', 0),
                calories=data['calories'],
                notes=None if message.text.lower() == 'нет' else message.text
            )

            session.add(workout)
            await session.flush()

            if data['workout_type'] == "strength":
                for exercise_data in data.get('exercises', []):
                    exercise = Exercise(
                        workout_id=workout.workout_id,
                        name=exercise_data['name'],
                        sets=exercise_data['sets'],
                        reps=exercise_data['reps'],
                        weight=exercise_data['weight']
                    )
                    session.add(exercise)

            await session.commit()

            response = (
                f"✅ Тренировка сохранена!\n"
                f"Тип: {data['workout_type']}\n"
                f"Длительность: {data['duration']} мин.\n"
                f"Калории: {data['calories']} ккал\n"
            )

            if data['workout_type'] == "strength":
                response += "\nУпражнения:\n"
                for i, ex in enumerate(data.get('exercises', []), 1):
                    response += (
                        f"{i}. {ex['name']} - "
                        f"{ex['sets']}x{ex['reps']} по {ex['weight']}кг\n"
                    )

            await message.answer(
                response,
                reply_markup=get_main_menu(user.is_admin)
            )
        except Exception as e:
            await session.rollback()
            await message.answer(
                "❌ Ошибка сохранения. Попробуйте позже.",
                reply_markup=get_main_menu(message.from_user.id)
            )
            logging.error(f"Workout save error: {e}")
        finally:
            await state.clear()


@router.message(PaginationStates.viewing_workouts, F.text == "✏️ Редактировать")
async def select_workout_to_edit(message: Message, state: FSMContext):
    """Выбор тренировки для редактирования"""
    data = await state.get_data()
    current_page = data['current_page']
    user_id = data['user_id']

    async for session in get_db_session():
        workouts = await session.execute(
            select(Workout)
            .where(Workout.user_id == user_id)
            .order_by(desc(Workout.date))
            .offset((current_page - 1) * 5)
            .limit(5)
        )
        workouts = workouts.scalars().all()

        builder = ReplyKeyboardBuilder()
        for i, workout in enumerate(workouts, 1):
            builder.add(KeyboardButton(text=f"✏️ {i}"))
        builder.row(KeyboardButton(text="❌ Отмена"))

        await message.answer(
            "Выберите номер тренировки для редактирования:",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
        await state.set_state(EditWorkoutStates.waiting_for_workout_to_edit)
        await state.update_data(workouts=[w.workout_id for w in workouts])


@router.message(EditWorkoutStates.waiting_for_workout_to_edit, F.text.regexp(r'^✏️\s*\d+$'))
async def select_field_to_edit(message: Message, state: FSMContext):
    """Выбор поля для редактирования"""
    try:
        data = await state.get_data()
        workout_index = int(message.text.split('✏️')[1].strip()) - 1

        if workout_index < 0 or workout_index >= len(data['workouts']):
            await message.answer("Неверный номер тренировки.")
            return

        workout_id = data['workouts'][workout_index]

        async for session in get_db_session():
            workout = await session.get(Workout, workout_id)
            if not workout:
                await message.answer("Тренировка не найдена.")
                return

            builder = ReplyKeyboardBuilder()
            fields = ["Тип тренировки", "Дата и время", "Длительность", "Калории", "Заметки"]

            if workout.type == "strength":
                fields.append("Упражнения")
            elif workout.type in DISTANCE_WORKOUTS:
                fields.append("Дистанция")

            for field in fields:
                builder.add(KeyboardButton(text=field))
            builder.row(KeyboardButton(text="❌ Отмена"))

            await state.update_data(workout_id=workout_id)
            await message.answer(
                "Выберите что хотите изменить:",
                reply_markup=builder.as_markup(resize_keyboard=True))
            await state.set_state(EditWorkoutStates.waiting_for_edit_choice)

    except Exception as e:
        logging.error(f"Ошибка выбора тренировки: {e}")
        await message.answer("❌ Произошла ошибка при выборе тренировки")


@router.message(EditWorkoutStates.waiting_for_edit_choice)
async def process_edit_choice(message: Message, state: FSMContext):
    """Обработка выбора поля для редактирования"""
    data = await state.get_data()
    workout_id = data['workout_id']

    async for session in get_db_session():
        workout = await session.get(Workout, workout_id)

        if message.text == "Упражнения" and workout.type == "strength":
            await handle_edit_exercises(message, state, workout_id)
            return

        field_mapping = {
            "Тип тренировки": "type",
            "Дата и время": "date",
            "Длительность": "duration",
            "Дистанция": "distance",
            "Калории": "calories",
            "Заметки": "notes"
        }

        if message.text not in field_mapping:
            await message.answer("Пожалуйста, выберите поле из списка.")
            return

        field = field_mapping[message.text]
        await state.update_data(edit_field=field)

        prompts = {
            "type": "Выберите новый тип тренировки:",
            "date": "Введите новую дату и время (ДД.ММ.ГГГГ ЧЧ:ММ):",
            "duration": "Введите новую длительность (минуты):",
            "distance": "Введите новую дистанцию (км):",
            "calories": "Введите новое количество калорий:",
            "notes": "Введите новые заметки:"
        }

        if field == "type":
            await message.answer(
                prompts[field],
                reply_markup=get_workout_types()
            )
        else:
            await message.answer(
                prompts[field],
                reply_markup=ReplyKeyboardRemove()
            )

        await state.set_state(EditWorkoutStates.waiting_for_new_value)


async def handle_edit_exercises(message: Message, state: FSMContext, workout_id: int):
    """Обработка редактирования упражнений"""
    async for session in get_db_session():
        exercises = await session.execute(
            select(Exercise)
            .where(Exercise.workout_id == workout_id)
            .order_by(Exercise.exercise_id)
        )
        exercises = exercises.scalars().all()

        if not exercises:
            await message.answer("В этой тренировке нет упражнений.")
            return

        builder = ReplyKeyboardBuilder()
        for i, exercise in enumerate(exercises, 1):
            builder.add(KeyboardButton(text=f"🏋️‍ Упражнение {i}: {exercise.name}"))
        builder.row(KeyboardButton(text="❌ Отмена"))  # Убрали кнопку добавления

        await message.answer(
            "Выберите упражнение для редактирования:",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
        await state.update_data(
            exercises=[e.exercise_id for e in exercises],
            workout_id=workout_id
        )
        await state.set_state(EditExerciseStates.waiting_for_exercise_to_edit)


@router.message(EditExerciseStates.waiting_for_exercise_to_edit, F.text.regexp(r'^🏋️‍ Упражнение \d+:'))
async def select_exercise_field(message: Message, state: FSMContext):
    """Выбор поля упражнения для редактирования"""
    try:
        # Извлекаем номер упражнения из текста кнопки
        exercise_num = int(message.text.split()[2].replace(':', ''))
        data = await state.get_data()
        exercise_id = data['exercises'][exercise_num - 1]

        builder = ReplyKeyboardBuilder()
        fields = [
            "Название упражнения",
            "Количество подходов",
            "Количество повторений",
            "Вес"
        ]

        for field in fields:
            builder.add(KeyboardButton(text=field))
        builder.row(KeyboardButton(text="❌ Отмена"))
        builder.row(KeyboardButton(text="🗑️ Удалить упражнение"))

        await state.update_data(
            exercise_id=exercise_id,
            exercise_index=exercise_num - 1
        )
        await message.answer(
            "Выберите что хотите изменить:",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
        await state.set_state(EditExerciseStates.waiting_for_exercise_field)
    except Exception as e:
        logging.error(f"Ошибка выбора упражнения: {e}")
        await message.answer("❌ Произошла ошибка при выборе упражнения")


@router.message(EditWorkoutStates.waiting_for_workout_to_edit, F.text == "❌ Отмена")
@router.message(EditWorkoutStates.waiting_for_edit_choice, F.text == "❌ Отмена")
@router.message(EditWorkoutStates.waiting_for_new_value, F.text == "❌ Отмена")
@router.message(EditExerciseStates.waiting_for_exercise_to_edit, F.text == "❌ Отмена")
@router.message(EditExerciseStates.waiting_for_exercise_field, F.text == "❌ Отмена")
@router.message(EditExerciseStates.waiting_for_new_exercise_value, F.text == "❌ Отмена")
async def cancel_edit(message: Message, state: FSMContext):
    """Обработка отмены редактирования"""
    await state.clear()
    await show_workouts(message, state)


@router.message(EditExerciseStates.waiting_for_exercise_field)
async def process_exercise_field_choice(message: Message, state: FSMContext):
    """Обработка выбора поля упражнения"""
    if message.text == "🗑️ Удалить упражнение":
        await delete_exercise(message, state)
        return

    field_mapping = {
        "Название упражнения": "name",
        "Количество подходов": "sets",
        "Количество повторений": "reps",
        "Вес": "weight"
    }

    if message.text not in field_mapping:
        await message.answer("Пожалуйста, выберите поле из списка.")
        return

    field = field_mapping[message.text]
    await state.update_data(exercise_field=field)

    prompts = {
        "name": "Введите новое название упражнения:",
        "sets": "Введите новое количество подходов:",
        "reps": "Введите новое количество повторений:",
        "weight": "Введите новый вес (кг):"
    }

    await message.answer(
        prompts[field],
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(EditExerciseStates.waiting_for_new_exercise_value)


async def delete_exercise(message: Message, state: FSMContext):
    """Удаление упражнения"""
    data = await state.get_data()
    exercise_id = data['exercise_id']
    workout_id = data['workout_id']

    try:
        async for session in get_db_session():
            exercise = await session.get(Exercise, exercise_id)
            await session.delete(exercise)
            await session.commit()
            await message.answer("✅ Упражнение удалено!")

            remaining = await session.execute(
                select(Exercise).where(Exercise.workout_id == workout_id))
            remaining = remaining.scalars().all()

            if not remaining:
                await message.answer("В тренировке больше нет упражнений.")
                await state.set_state(None)
                await show_workouts(message, state)
            else:
                await handle_edit_exercises(message, state, workout_id)

    except Exception as e:
        logging.error(f"Ошибка при удалении упражнения: {e}")
        await message.answer("❌ Произошла ошибка при удалении упражнения.")


@router.message(EditExerciseStates.waiting_for_new_exercise_value)
async def save_edited_exercise(message: Message, state: FSMContext):
    """Сохранение изменений в упражнении"""
    data = await state.get_data()
    field = data['exercise_field']
    exercise_id = data['exercise_id']
    workout_id = data['workout_id']

    try:
        async for session in get_db_session():
            exercise = await session.get(Exercise, exercise_id)

            if field in ["sets", "reps", "weight"]:
                try:
                    value = int(message.text)
                    if value <= 0:
                        raise ValueError
                    setattr(exercise, field, value)
                except ValueError:
                    await message.answer("Введите целое число больше 0.")
                    return
            else:
                setattr(exercise, field, message.text)

            await session.commit()
            await message.answer("✅ Изменения сохранены!")

            await state.set_state(EditExerciseStates.waiting_for_exercise_field)
            await select_exercise_field(message, state)

    except Exception as e:
        logging.error(f"Ошибка при редактировании упражнения: {e}")
        await message.answer("❌ Произошла ошибка при сохранении изменений.")


@router.message(EditExerciseStates.waiting_for_exercise_to_edit, F.text == "➕ Добавить упражнение")
async def add_new_exercise(message: Message, state: FSMContext):
    """Добавление нового упражнения к силовой тренировке"""
    data = await state.get_data()
    workout_id = data['workout_id']

    await state.update_data(
        workout_id=workout_id,
        is_new_exercise=True
    )
    await message.answer(
        "Введите название нового упражнения:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(WorkoutStates.waiting_for_exercise_name)


@router.message(EditWorkoutStates.waiting_for_new_value)
async def save_edited_field(message: Message, state: FSMContext):
    """Сохранение измененного поля"""
    data = await state.get_data()
    workout_id = data['workout_id']
    field = data['edit_field']

    try:
        async for session in get_db_session():
            workout = await session.get(Workout, workout_id)

            if field == "type":
                if message.text not in WORKOUT_TYPES:
                    await message.answer("Пожалуйста, выберите тип из списка.")
                    return
                setattr(workout, field, WORKOUT_TYPES[message.text])

            elif field == "date":
                try:
                    new_date = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
                    setattr(workout, field, new_date)
                except ValueError:
                    await message.answer("Неверный формат даты. Используйте ДД.ММ.ГГГГ ЧЧ:ММ")
                    return

            elif field in ["duration", "distance", "calories"]:
                try:
                    value = float(message.text)
                    if value <= 0:
                        raise ValueError
                    setattr(workout, field, value)
                except ValueError:
                    await message.answer("Введите положительное число.")
                    return

            elif field == "notes":
                setattr(workout, field, message.text if message.text.lower() != "нет" else None)

            await session.commit()
            await message.answer("✅ Изменения сохранены!")

            await state.set_state(None)
            await show_workouts(message, state)

    except Exception as e:
        logging.error(f"Ошибка при редактировании тренировки: {e}")
        await message.answer("❌ Произошла ошибка при сохранении изменений.")


@router.message(PaginationStates.viewing_workouts, F.text == "🗑️ Удалить")
async def select_workout_to_delete(message: Message, state: FSMContext):
    """Выбор тренировки для удаления"""
    data = await state.get_data()
    current_page = data['current_page']
    user_id = data['user_id']

    async for session in get_db_session():
        workouts = await session.execute(
            select(Workout)
            .where(Workout.user_id == user_id)
            .order_by(desc(Workout.date))
            .offset((current_page - 1) * 5)
            .limit(5)
        )
        workouts = workouts.scalars().all()

        builder = ReplyKeyboardBuilder()
        for i, workout in enumerate(workouts, 1):
            builder.add(KeyboardButton(text=f"🗑️ {i}"))
        builder.row(KeyboardButton(text="❌ Отмена"))

        await message.answer(
            "Выберите номер тренировки для удаления:",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
        await state.set_state(DeleteWorkoutStates.waiting_for_workout_to_delete)
        await state.update_data(workouts=[w.workout_id for w in workouts])


@router.message(DeleteWorkoutStates.waiting_for_workout_to_delete, F.text.regexp(r'^🗑️\s*\d+$'))
async def confirm_delete_workout(message: Message, state: FSMContext):
    """Подтверждение удаления тренировки"""
    try:
        workout_index = int(message.text.split('🗑️')[1].strip()) - 1
        data = await state.get_data()

        if workout_index < 0 or workout_index >= len(data['workouts']):
            await message.answer("Неверный номер тренировки.")
            return

        workout_id = data['workouts'][workout_index]

        async for session in get_db_session():
            workout = await session.get(Workout, workout_id)
            if not workout:
                await message.answer("Тренировка не найдена.")
                return

            response = (
                f"Вы действительно хотите удалить эту тренировку?\n\n"
                f"Тип: {workout.type}\n"
                f"Дата: {workout.date.strftime('%d.%m.%Y %H:%M')}\n"
                f"Длительность: {workout.duration} мин.\n"
            )

            if workout.type == "strength":
                exercises = await session.execute(
                    select(Exercise).where(Exercise.workout_id == workout.workout_id))
                exercises = exercises.scalars().all()

                if exercises:
                    response += "\nУпражнения:\n"
                    for i, ex in enumerate(exercises, 1):
                        response += f"{i}. {ex.name} ({ex.sets}x{ex.reps} по {ex.weight}кг)\n"

            builder = ReplyKeyboardBuilder()
            builder.row(KeyboardButton(text="✅ Да, удалить"))
            builder.row(KeyboardButton(text="❌ Нет, отменить"))

            await state.update_data(workout_id=workout_id)
            await message.answer(
                response,
                reply_markup=builder.as_markup(resize_keyboard=True)
            )
            await state.set_state(DeleteWorkoutStates.waiting_for_delete_confirmation)

    except Exception as e:
        logging.error(f"Ошибка выбора тренировки для удаления: {e}")
        await message.answer("❌ Произошла ошибка при выборе тренировки")


@router.message(DeleteWorkoutStates.waiting_for_delete_confirmation, F.text == "✅ Да, удалить")
async def delete_workout_confirmed(message: Message, state: FSMContext):
    """Удаление тренировки после подтверждения"""
    data = await state.get_data()
    workout_id = data['workout_id']

    try:
        async for session in get_db_session():
            # Сначала удаляем все упражнения (если это силовая тренировка)
            await session.execute(
                delete(Exercise).where(Exercise.workout_id == workout_id))

            # Затем удаляем саму тренировку
            await session.execute(
                delete(Workout).where(Workout.workout_id == workout_id))

            await session.commit()

            await message.answer(
                "✅ Тренировка успешно удалена!",
                reply_markup=get_main_menu()
            )
            await state.clear()

            # Показываем обновленный список тренировок
            await show_workouts(message, state)

    except Exception as e:
        logging.error(f"Ошибка при удалении тренировки: {e}")
        await message.answer("❌ Произошла ошибка при удалении тренировки.")


@router.message(DeleteWorkoutStates.waiting_for_delete_confirmation, F.text == "❌ Нет, отменить")
@router.message(DeleteWorkoutStates.waiting_for_workout_to_delete, F.text == "❌ Отмена")
async def cancel_delete_workout(message: Message, state: FSMContext):
    """Отмена удаления тренировки"""
    await state.clear()
    await show_workouts(message, state)