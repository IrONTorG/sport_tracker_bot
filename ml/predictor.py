import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import timedelta

def predict_future_workouts(dates, durations, calories, steps=7):
    """
    Простая регрессия по времени: предсказывает длительность и калории на будущее
    """
    # Преобразуем даты в числовой формат (кол-во дней от начала)
    base_date = min(dates)
    x = np.array([(d - base_date).days for d in dates]).reshape(-1, 1)

    duration_model = LinearRegression().fit(x, durations)
    calories_model = LinearRegression().fit(x, calories)

    # Генерация будущих дней
    future_days = np.array([x[-1][0] + i for i in range(1, steps + 1)]).reshape(-1, 1)
    future_dates = [base_date + timedelta(days=int(day[0])) for day in future_days]

    future_durations = duration_model.predict(future_days)
    future_calories = calories_model.predict(future_days)

    return future_dates, future_durations, future_calories