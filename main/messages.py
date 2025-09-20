from dataclasses import dataclass
from autogen_core import AgentId
import glob
import os
import random

@dataclass
class Message:
    content: str


def find_recipient() -> AgentId:
    try:
        # Look for agent Python files in the same directory as this file (i.e. the `main` package)
        main_dir = os.path.dirname(__file__)
        agent_files = glob.glob(os.path.join(main_dir, "agent*.py"))
        # Extract just the base filename (without directory and extension)
        agent_names = [os.path.splitext(os.path.basename(file))[0] for file in agent_files]
        # Remove the template `agent.py` if it exists in the list
        if "agent" in agent_names:
            agent_names.remove("agent")
        # If no dynamically-generated agents exist yet, fall back gracefully
        if not agent_names:
            raise ValueError("No generated agents found")
        agent_name = random.choice(agent_names)
        print(f"Selecting agent for refinement: {agent_name}")
        return AgentId(agent_name, "default")
    except Exception as e:
        print(f"Exception finding recipient: {e}")
        return AgentId("agent1", "default")
