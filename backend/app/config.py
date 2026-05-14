from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "mysql+pymysql://nexabank_user:nexabank_password@db:3306/nexabank_db"

    # Security
    JWT_SECRET_KEY: str = "change_this_to_a_very_long_random_secret_key_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # App
    APP_NAME: str = "NexaBank"
    ENVIRONMENT: str = "production"
    # BASE_URL should point to the Frontend (e.g. Vercel) so verification links work correctly
    BASE_URL: str = "http://localhost:8000"



settings = Settings()
