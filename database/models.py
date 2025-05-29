from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, BigInteger, Text
from sqlalchemy.orm import relationship
from .session import Base
from sqlalchemy import Time


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(Text)
    registration_date = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)

    workouts = relationship("Workout", back_populates="user")
    reminders = relationship("Reminder", back_populates="user")


class Workout(Base):
    __tablename__ = "workouts"

    workout_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime, nullable=False)
    type = Column(String(50), nullable=False)  # Убрали collation
    duration = Column(Float)
    distance = Column(Float)
    calories = Column(Float)
    notes = Column(Text)  # Убрали collation

    user = relationship("User", back_populates="workouts")
    exercises = relationship("Exercise", back_populates="workout")


class Exercise(Base):
    __tablename__ = "exercises"

    exercise_id = Column(Integer, primary_key=True, autoincrement=True)
    workout_id = Column(Integer, ForeignKey("workouts.workout_id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    sets = Column(Integer)
    reps = Column(Integer)
    weight = Column(Integer)  # Обратите внимание: в SQL у вас INT, в модели было Float

    workout = relationship("Workout", back_populates="exercises")


class Reminder(Base):
    __tablename__ = "reminders"

    reminder_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    reminder_text = Column(Text)
    reminder_time = Column(Time, nullable=False)
    day_of_week = Column(Text)


    user = relationship("User", back_populates="reminders")