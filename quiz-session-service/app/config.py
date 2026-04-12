from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret: str = "supersecretjwtkey_changethisinproduction"
    jwt_algorithm: str = "HS256"
    redis_url: str = "redis://redis:6379"
    deck_service_url: str = "http://deck-service:8001"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
