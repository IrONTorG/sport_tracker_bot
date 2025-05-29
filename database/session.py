from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import text
from config import Config
import logging

# Настройка логгирования
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Формирование URL подключения
SQLALCHEMY_DATABASE_URL = (
    f"mysql+asyncmy://{Config.DB_USER}:{Config.DB_PASS}@"
    f"{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    "?charset=utf8mb4"
)
# Создаем асинхронный движок
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True
)

# Асинхронная фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)

Base = declarative_base()

async def get_db_session() -> AsyncSession:
    """Создает и возвращает новую сессию"""
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()

async def check_db_connection():
    """Проверка подключения к БД"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Подключение к БД успешно")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        raise