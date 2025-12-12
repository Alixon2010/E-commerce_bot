from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, declared_attr, sessionmaker

from settings import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False, future=True)


class Base(DeclarativeBase):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + "s"


async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
