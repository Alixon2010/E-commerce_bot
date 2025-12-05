from datetime import datetime, timedelta
from sqlalchemy import String, BigInteger, select, update, Integer, func, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import mapped_column, Mapped

from database.base import Base


class User(Base):
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    token: Mapped[str | None] = mapped_column(String, nullable=True)
    exp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    @property
    def exp_time(self):
        if self.exp:
            return self.updated_at + timedelta(hours=self.exp)
        return None

async def get_user(session: AsyncSession, chat_id: int):
    stmt = select(User).where(User.chat_id == chat_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, chat_id: int):
    user = User(chat_id=chat_id)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_token(session: AsyncSession, chat_id: int, token: str, exp: int):
    stmt = (
        update(User)
        .where(User.chat_id == chat_id)
        .values(token=token, exp=exp)
    )
    await session.execute(stmt)
    await session.commit()
