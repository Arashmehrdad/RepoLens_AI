"""Environment loading helpers."""

from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    """Load environment variables from the repository `.env` file."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_path)
