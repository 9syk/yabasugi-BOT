import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

if POSTGRES_PASSWORD is None:
    raise ValueError("POSTGRES_PASSWORD is not set")

DATABASE_URL = (
    f"postgresql+asyncpg://postgres:{POSTGRES_PASSWORD}@db:5432/yabasugibot"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
