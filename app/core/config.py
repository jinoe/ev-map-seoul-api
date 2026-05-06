from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "EV Map Seoul API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    PORT: int = 400
    ALLOWED_ORIGINS: list[str] = ["*"]

    # "server" → localhost MongoDB, "local" → AWS MongoDB (13.125.235.209)
    APP_ENV: str = "local"

    # MongoDB — MONGODB_URI 를 직접 지정하면 APP_ENV 기반 자동 선택보다 우선
    MONGODB_URI: str = ""
    MONGODB_USER: str = ""
    MONGODB_PASSWORD: str = ""
    MONGODB_PORT: int = 27017
    MONGODB_DB_NAME: str = "ev_charger"

    @computed_field
    @property
    def mongodb_connection_uri(self) -> str:
        if self.MONGODB_URI:
            return self.MONGODB_URI
        host = "localhost" if self.APP_ENV == "server" else "13.125.235.209"
        if self.MONGODB_USER and self.MONGODB_PASSWORD:
            return (
                f"mongodb://{self.MONGODB_USER}:{self.MONGODB_PASSWORD}"
                f"@{host}:{self.MONGODB_PORT}/{self.MONGODB_DB_NAME}?authSource=admin"
            )
        return f"mongodb://{host}:{self.MONGODB_PORT}/{self.MONGODB_DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
