from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "EV Map Seoul API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    PORT: int = 400

    ALLOWED_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
