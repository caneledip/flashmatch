from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost/auth/callback"

    jwt_secret: str = "supersecretjwtkey_changethisinproduction"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    user_db_url: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
