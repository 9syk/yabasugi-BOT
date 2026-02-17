from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column
from db import Base


class MessageCount(Base):
    __tablename__ = "message_counts"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class TotalCount(Base):
    __tablename__ = "total_counts"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class GuildSettings(Base):
    __tablename__ = "guild_settings"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ranking_channel_id: Mapped[int] = mapped_column(BigInteger)
