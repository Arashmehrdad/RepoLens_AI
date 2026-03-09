from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_path)