import asyncio
import glob
import json
import os
import sys
from typing import Tuple, Optional

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost, GrpcWorkerAgentRuntime
from autogen_core import AgentId

from main.creator import Creator
from main import messages
from main.upload_to_gcp import upload_to_gcp
from main import constants

HOW_MANY_AGENTS = constants.TOTAL_AGENTS_CREATED_SIMULTANEOUSLY


async def _create_and_message(worker: GrpcWorkerAgentRuntime, creator_id: AgentId, i: int, prompt: str):
    try:
        payload = json.dumps({
            "filename": f"agent{i}.py",
            "prompt": prompt,
        })
        result = await worker.send_message(messages.Message(content=payload), creator_id)
        ideas_dir = os.path.join(os.path.dirname(__file__), os.pardir, "ideas")
        ideas_dir = os.path.abspath(ideas_dir)
        if not os.path.isdir(ideas_dir):
            os.makedirs(ideas_dir)
        with open(os.path.join(ideas_dir, f"idea{i}.md"), "w", encoding="utf-8") as f:
            f.write(result.content)
    except Exception as e:
        print(f"Failed to run worker {i} due to exception: {e}")


async def _run_agents(prompt: str, how_many: int = HOW_MANY_AGENTS):
    host = GrpcWorkerAgentRuntimeHost(address="localhost:50051")
    host.start()
    worker = GrpcWorkerAgentRuntime(host_address="localhost:50051")
    await worker.start()
    await Creator.register(worker, "Creator", lambda: Creator("Creator"))
    creator_id = AgentId("Creator", "default")
    coroutines = [_create_and_message(worker, creator_id, i, prompt) for i in range(1, how_many + 1)]
    await asyncio.gather(*coroutines)
    try:
        await worker.stop()
        await host.stop()
    except Exception as e:
        print(e)


def _read_last_idea_md() -> Optional[str]:
    ideas_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "ideas"))
    if not os.path.isdir(ideas_dir):
        return None
    paths = glob.glob(os.path.join(ideas_dir, "idea*.md"))
    if not paths:
        return None
    # Choose most recently modified file
    latest = max(paths, key=os.path.getmtime)
    try:
        with open(latest, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def run_pipeline(agent_prompt: str, how_many: int = HOW_MANY_AGENTS) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Run the full pipeline: create agents, generate ideas, capture last idea content, upload zips to GCP.

    Returns:
        (agents_signed_url, ideas_signed_url, last_idea_markdown)
    """
    asyncio.run(_run_agents(agent_prompt, how_many=how_many))
    last_idea = _read_last_idea_md()
    urls = upload_to_gcp()  # deletes local idea*.md and agent*.py
    agents_url = urls.get("agents_signed_url") if isinstance(urls, dict) else None
    ideas_url = urls.get("ideas_signed_url") if isinstance(urls, dict) else None
    return agents_url, ideas_url, last_idea
