#!/usr/bin/env python
import os

from huggingface_hub import HfApi


SPACE_ID = os.getenv("HF_SPACE_ID", "kaushikpaul/Auto-AI-Agents-Creator")

ALLOW_PATTERNS = [
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "LICENSE",
    "main/**",
    "ideas/.gitkeep",
]

IGNORE_PATTERNS = [
    "main/__pycache__/**",
    "main/error.txt",
]

DELETE_PATTERNS = [
    ".venv/**",
    "venv/**",
    "env/**",
    ".env",
    ".idea/**",
    ".vscode/**",
    ".ruff_cache/**",
    "__pycache__/**",
    "main/__pycache__/**",
    "main/error.txt",
    "ignore.txt",
]


def main() -> None:
    print(f"Deploying to Hugging Face Space: {SPACE_ID}")
    HfApi().upload_folder(
        repo_id=SPACE_ID,
        repo_type="space",
        folder_path=".",
        allow_patterns=ALLOW_PATTERNS,
        ignore_patterns=IGNORE_PATTERNS,
        delete_patterns=DELETE_PATTERNS,
        commit_message="Deploy Space",
    )
    print(f"Space available at https://huggingface.co/spaces/{SPACE_ID}")


if __name__ == "__main__":
    main()
