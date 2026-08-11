import os

from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv(override=True)

MODEL_INFO = {
    "family": "unknown",
    "vision": False,
    "json_output": False,
    "function_calling": False,
    "structured_output": False,
}


def _env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def create_model_client(*, temperature: float) -> ChatCompletionClient:
    return OpenAIChatCompletionClient(
        model=_env_required("MODEL"),
        base_url=_env_required("BASE_URL"),
        api_key=_env_required("API_KEY"),
        model_info=MODEL_INFO,
        temperature=temperature,
    )
