from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class User(Base):
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    token: Mapped[str | None] = mapped_column(String, nullable=True)
    exp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    @property
    def exp_time(self):
        """Время истечения токена"""
        if self.exp and self.updated_at:
            return self.updated_at + timedelta(hours=self.exp)
        return None

    @property
    def is_expired(self):
        """Проверка истек ли токен"""
        exp_time = self.exp_time
        if not exp_time:
            return True
        return datetime.now(timezone.utc) > exp_time


async def get_user(session: AsyncSession, chat_id: int):
    """Получить пользователя"""
    stmt = select(User).where(User.chat_id == chat_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_user(session: AsyncSession, chat_id: int):
    """Получить или создать пользователя без ошибок"""
    user = await get_user(session, chat_id)
    if user:
        return user

    try:
        user = User(chat_id=chat_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    except IntegrityError:
        await session.rollback()
        return await get_user(session, chat_id)
    except Exception as e:
        await session.rollback()
        raise e


async def update_user_token(session: AsyncSession, chat_id: int, token: str, exp: int):
    """Обновить токен пользователя"""
    stmt = update(User).where(User.chat_id == chat_id).values(token=token, exp=exp)
    await session.execute(stmt)
    await session.commit()
