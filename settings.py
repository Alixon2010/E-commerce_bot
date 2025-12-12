from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    HOST: str = "http://127.0.0.1:8000"

    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_SECRET_KEY: str

    DB_PORT: int
    DB_HOST: str
    DB_PASSWORD: str
    DB_USER: str
    DB_NAME: str

    @property
    def DATABASE_URL(self):
        return (f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@"
                f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
