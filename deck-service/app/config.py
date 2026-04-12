from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret: str = "supersecretjwtkey_changethisinproduction"
    jwt_algorithm: str = "HS256"
    deck_db_url: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
