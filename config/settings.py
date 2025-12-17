import os
from pathlib import Path
from typing import Tuple


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = parse_env_line(stripped)
        os.environ.setdefault(key, value)


def parse_env_line(line: str) -> Tuple[str, str]:
    key, value = line.split("=", 1)
    return key.strip(), value.strip().strip('"').strip("'")


load_env_file()


class Settings:
    DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
    DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
    DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG", "main")
    DATABRICKS_SCHEMA = os.getenv("DATABRICKS_SCHEMA", "default")
    DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")
    VECTOR_SEARCH_ENDPOINT = os.getenv("VECTOR_SEARCH_ENDPOINT")
    VECTOR_SEARCH_INDEX = os.getenv("VECTOR_SEARCH_INDEX", "documents_index")
    VECTOR_SEARCH_EMBEDDING_MODEL = os.getenv("VECTOR_SEARCH_EMBEDDING_MODEL", "text-embedding-3-small")
    VECTOR_SEARCH_LOCAL_DIM = int(os.getenv("VECTOR_SEARCH_LOCAL_DIM", "384"))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


settings = Settings()
