from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "mysql+pymysql://bankuser:bankpassword@db:3306/bankdb"

    # Security
    SECRET_KEY: str = "change_this_to_a_very_long_random_secret_key_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # App
    APP_NAME: str = "NexaBank"
    FRONTEND_URL: str = "http://localhost:8000"


settings = Settings()
