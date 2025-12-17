import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
    DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


settings = Settings()
