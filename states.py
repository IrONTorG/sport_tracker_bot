from aiogram.fsm.state import State, StatesGroup

class WorkoutStates(StatesGroup):
    """Состояния для добавления тренировки"""
    waiting_for_type = State()
    waiting_for_exercise_name = State()  # Только для силовой
    waiting_for_sets = State()  # Только для силовой
    waiting_for_reps = State()  # Только для силовой
    waiting_for_weight = State()  # Только для силовой
    waiting_for_duration = State()
    waiting_for_distance = State()  # Только для кардио
    waiting_for_calories = State()
    waiting_for_notes = State()
    waiting_for_more_exercises = State()

class UserStates(StatesGroup):
    waiting_for_new_name = State()

class AddExerciseStates(StatesGroup):
    waiting_for_add_more = State()


class DeleteWorkoutStates(StatesGroup):
    waiting_for_workout_to_delete = State()
    waiting_for_delete_confirmation = State()


class ReminderStates(StatesGroup):
    waiting_for_day = State()
    waiting_for_time = State()
    waiting_for_text = State()
    editing_text = State()
    editing_day = State()
    editing_time = State()

class EditExerciseStates(StatesGroup):
    waiting_for_exercise_to_edit = State()
    waiting_for_exercise_field = State()
    waiting_for_new_exercise_value = State()

class EditWorkoutStates(StatesGroup):
    waiting_for_workout_to_edit = State()
    waiting_for_edit_choice = State()
    waiting_for_new_value = State()
    waiting_for_user_search = State()
    waiting_for_export_format = State()

class AdminStates(StatesGroup):
    """Состояния для админ-панели"""
    waiting_for_user_id = State()       # Ожидание ID пользователя для бана
    waiting_for_ban_reason = State()    # Ожидание причины бана
    waiting_for_confirm = State()       # Ожидание подтверждения бана
    waiting_for_user_search = State()   # Ожидание ввода для поиска пользователя
    waiting_for_export_format = State() # Ожидание выбора формата экспорта
    waiting_for_user_message = State()
    waiting_for_ban_user = State()
    # Ожидание сообщения для пользователя  # Ожидание подтверждения бана

class StatsStates(StatesGroup):
    """Состояния для просмотра статистики"""
    waiting_for_period = State()        # Ожидание выбора периода
    waiting_for_type_filter = State()   # Ожидание выбора фильтра по типу