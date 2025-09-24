# Auto AI Agents Creator

[![Live Website](https://img.shields.io/badge/Live_Website-6c63ff?logo=rocket&logoColor=white&labelColor=5a52d3)](https://projects.kaushikpaul.pp.ua/auto-ai-agents)

An AI-powered agent factory where multiple AI agents collaborate to generate and refine ideas. Watch as these agents work in parallel, discuss concepts, and produce unique insights — all accessible through an intuitive Gradio interface.

This project is powered by Microsoft Autogen (AgentChat + Core + gRPC runtime). It spins up a Creator agent that generates new agent classes on the fly, registers them with a lightweight gRPC runtime, messages them with your prompt, and packages outputs to Google Cloud Storage (GCS) with signed download links.

## Live Demo
- [Visit the Live Website](https://projects.kaushikpaul.pp.ua/auto-ai-agents)

## Features
- __Multi-agent generation (Autogen)__
  - Uses `autogen_agentchat` and `autogen_core` with the gRPC worker runtime to create and interact with multiple agents concurrently.
- __One-click pipeline__
  - Enter a prompt → create agents → collect ideas → package ideas and generated agent code → upload to GCS → return signed URLs.
- __Polished Gradio UI__
  - Clean header, example loader, progress updates, and result boxes with copy buttons.
- __Artifact delivery via GCS__
  - Zips are uploaded to GCS and returned as time-limited signed URLs. Local source files are cleaned up automatically.
- __Model-flexible__
  - Uses OpenRouter-hosted models via an OpenAI-compatible client. Model and base URL are set in `main/constants.py`.

## Architecture Overview
- __UI__: `main/gradio_app.py` (entry launched by `main/app.py`)
- __Pipeline__: `main/pipeline.py`
  - Starts the Autogen gRPC runtime, generates agents, collects outputs, and triggers upload
- __Agents__: 
  - Template agent: `main/agent.py`
  - Creator agent (generates agents on the fly): `main/creator.py`
- __Cloud upload__: `main/upload_to_gcp.py` (bundles and uploads artifacts to GCS, returns signed URLs)
- __Configuration__: `main/constants.py` (OpenRouter base URL, model, number of agents)

## Prerequisites
- Python 3.10+
- A modern browser
- Accounts/keys:
  - OpenRouter API key (for model access)
  - Google Cloud Platform project, bucket, and service account with storage permissions

## Quick Start

### 1) Clone the repo
```bash
git clone https://github.com/Kaushik-Paul/Auto-AI-Agents-Creator.git
cd Auto-AI-Agents-Creator
```

### 2) (Optional) Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
```

### 3) Install dependencies
#### Option A — Install with uv (recommended)
1) Install uv
- Linux/macOS:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# ensure ~/.local/bin is on your PATH
export PATH="$HOME/.local/bin:$PATH"
```
- Windows (PowerShell):
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2) Sync dependencies
```bash
uv sync
```

#### Option B — Install with pip
```bash
pip install -r requirements.txt
```

### 4) Create a .env file
Create a `.env` file in the project root:

```ini
# ——— OpenRouter (LLM provider via OpenAI-compatible client) ———
OPENROUTER_API_KEY=your_openrouter_key

# ——— Google Cloud Storage (used by upload_to_gcp.py) ———
GCP_PROJECT_ID=your_gcp_project_id
GCP_BUCKET_NAME=your_bucket_name
# Base64-encoded service account JSON (e.g. cat service_account.json | base64 -w 0)
GCP_SERVICE_KEY=base64_encoded_service_account_json
```

Notes:
- The base URL and model for OpenRouter are configured in `main/constants.py`.
- `creator.py` loads `.env` automatically via `python-dotenv`.

### 5) Run locally
```bash
python -m main.app
# or
python main/app.py
```
Gradio will print a local URL (e.g., http://127.0.0.1:7860). Open it in your browser.

## Why Microsoft Autogen?

This project leverages **Microsoft Autogen** (specifically, the AgentChat and Core components with gRPC runtime) for its powerful multi-agent orchestration capabilities. Here's why Autogen was chosen:

- **Flexible Agent Architecture**
  - Autogen's `RoutedAgent` base class and message passing system enable clean separation of concerns while allowing agents to communicate seamlessly.
  - The gRPC runtime provides a lightweight, language-agnostic way to manage agent lifecycles.

- **Dynamic Agent Generation**
  - The `Creator` agent can generate and register new agent classes on the fly, enabling dynamic scaling of the agent workforce based on demand.
  - Each generated agent inherits from `RoutedAgent`, ensuring consistent behavior while allowing for unique system prompts and personalities.

- **Efficient Resource Management**
  - The gRPC worker pool efficiently manages agent instances, allowing for concurrent execution of multiple agents without the overhead of separate processes.
  - Resources are automatically cleaned up when agents complete their tasks.

- **Extensibility**
  - The architecture makes it easy to add new agent types or modify existing ones by simply creating new Python classes that inherit from `RoutedAgent`.
  - The system can be extended with custom tools and capabilities by implementing new message handlers.

- **Production-Ready**
  - Built-in support for cancellation tokens and timeouts ensures robust operation in production environments.
  - The gRPC foundation provides a solid base for distributed deployments if needed.

This implementation demonstrates how Autogen can be used to create sophisticated multi-agent systems that go beyond simple chat interfaces, enabling complex workflows and dynamic agent generation.

## Usage
1. Open the app in your browser.
2. Paste or write a prompt describing the agents/ideas you want.
3. Optionally click the example to autofill.
4. Click “Run Pipeline”.
5. After processing, you’ll get two signed URLs (ideas zip and agents zip) and a preview of the last generated idea.

## Configuration

### LLM Provider (OpenRouter)
- File: `main/constants.py`
  - `OPENROUTER_BASE_URL` (default: `https://openrouter.ai/api/v1`)
  - `OPENROUTER_MODEL` (e.g., `x-ai/grok-4-fast:free`)
- File: `main/creator.py`
  - Uses `OpenAIChatCompletionClient` with the base URL and API key from above.

### Number of Agents (Concurrency)
- File: `main/constants.py`
  - `TOTAL_AGENTS_CREATED_SIMULTANEOUSLY` at line 3 controls how many agents are created in parallel.
- File: `main/pipeline.py`
  - Reads the value from constants: `HOW_MANY_AGENTS = constants.TOTAL_AGENTS_CREATED_SIMULTANEOUSLY`

__Important warnings when increasing the agent count:__
- __Cost & rate limits__: More agents = more model calls → higher cost and potential throttling/rate limits.
- __Autonomy__: Agents are given a degree of freedom to act and generate content on their own. If you prefer tighter control, consider reducing the agent count and/or adjusting the system prompts (see below).

### Agent System Prompts
- You can adjust the system prompts to better fit your preferences:
  - `main/creator.py` lines 39–47 — Creator agent’s system message
  - `main/agent.py` lines 30–36 — Template agent’s system message

## Outputs & Cloud Uploads
- The app generates two downloadable archives:
  - A zip file containing all generated ideas (Markdown format)
  - A zip file containing the Python code for all generated agents
- Both files are uploaded to Google Cloud Storage and accessible via time-limited signed URLs
- Local temporary files are automatically cleaned up after upload

## Deployment
- The project is deployed here: [Live Website](https://projects.kaushikpaul.pp.ua/auto-ai-agents)

To deploy your own Space:
- Create a new Space (SDK: Gradio)
- Point the Space to run `python -m main.app` (or equivalent) as the entry
- Configure Secrets in the Space settings:
  - `OPENROUTER_API_KEY`
  - `GCP_PROJECT_ID`, `GCP_BUCKET_NAME`, `GCP_SERVICE_KEY`
- Ensure the Python version is compatible with the versions in `requirements.txt`.

## Troubleshooting
- __Missing or invalid GCP variables__
  - Ensure `GCP_PROJECT_ID`, `GCP_BUCKET_NAME`, and a valid base64 `GCP_SERVICE_KEY` (service account JSON) are set.
- __OpenRouter authentication__
  - Confirm `OPENROUTER_API_KEY` is present and the selected `OPENROUTER_MODEL` in `main/constants.py` is accessible to your account.
- __No URLs returned__
  - If there were no generated files or the upload failed, signed URLs may be empty. Check logs and GCP permissions.
- __Port conflicts__
  - The Autogen gRPC runtime uses `localhost:50051`. If another service is using this port, stop it or change the address in `main/pipeline.py`.

## Tech Stack
- __Python__: 3.10+
- __Frameworks/Libraries__: Microsoft Autogen (AgentChat/Core/Ext), Gradio 5, Google Cloud Storage, python-dotenv, requests, httpx
- __Runtime__: Autogen gRPC worker runtime (local ephemeral host)
- __UI__: Gradio Blocks with progress and results

## Security & Privacy
- Do not commit `.env` or credentials.
- Use least-privilege service accounts on GCP. Signed URLs are short-lived by default (10 minutes).
- Be mindful that increasing agent count increases API usage and cost.

## License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgements
- Microsoft Autogen team and contributors
- Hugging Face Spaces for hosting