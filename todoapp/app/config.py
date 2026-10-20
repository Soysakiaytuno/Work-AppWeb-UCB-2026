import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    "postgresql://todo:todo@localhost:5432/todoapp",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False