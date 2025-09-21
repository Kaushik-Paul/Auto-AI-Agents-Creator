import importlib
import os
import sys
import logging
import json
from dotenv import load_dotenv

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from autogen_core import MessageContext, RoutedAgent, message_handler
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import TRACE_LOGGER_NAME
from autogen_core import AgentId

from main import messages
from main import constants

load_dotenv(override=True)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(TRACE_LOGGER_NAME)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = constants.OPENROUTER_BASE_URL
openrouter_model = constants.OPENROUTER_MODEL


class Creator(RoutedAgent):

    # Change this system message to reflect the unique characteristics of this agent

    system_message = """
    You are an Agent that is able to create new AI Agents.
    You receive a template in the form of Python code that creates an Agent using Autogen Core and Autogen Agentchat.
    You should use this template to create a new Agent with a unique system message that is different from the template,
    and reflects their unique characteristics, interests and goals.
    You can choose to keep their overall goal the same, or change it.
    You can choose to take this Agent in a completely different direction. The only requirement is that the class must be named Agent,
    and it must inherit from RoutedAgent and have an __init__ method that takes a name parameter.
    Also avoid environmental interests - try to mix up the business verticals so that every agent is different.
    Respond only with the python code, no other text, and no markdown code blocks.
    """


    def __init__(self, name) -> None:
        super().__init__(name)
        model_client = OpenAIChatCompletionClient(
            model=openrouter_model,
            base_url=OPENROUTER_BASE_URL,
            api_key=openrouter_api_key,
            model_info={
                "family": "xAI",
                "vision": True,
                "json_output": True,
                "function_calling": True,
                "structured_output": True
            },
            temperature=1.0
        )
        self._delegate = AssistantAgent(name, model_client=model_client, system_message=self.system_message)

    def get_user_prompt(self):
        prompt = "Please generate a new Agent based strictly on this template. Stick to the class structure. \
            Respond only with the python code, no other text, and no markdown code blocks.\n\n\
            Be creative about taking the agent in a new direction, but don't change method signatures.\n\n\
            Here is the template:\n\n"
        with open("main/agent.py", "r", encoding="utf-8") as f:
            template = f.read()
        return prompt + template   
        

    @message_handler
    async def handle_my_message_type(self, message: messages.Message, ctx: MessageContext) -> messages.Message:
        # Support both legacy plain filename and JSON payload with {"filename", "prompt"}
        filename = message.content
        prompt = "Give me an idea"
        try:
            parsed = json.loads(message.content)
            if isinstance(parsed, dict):
                filename = parsed.get("filename", filename)
                prompt = parsed.get("prompt", prompt)
        except Exception:
            pass
        agent_name = filename.split(".")[0]
        text_message = TextMessage(content=self.get_user_prompt(), source="user")
        response = await self._delegate.on_messages([text_message], ctx.cancellation_token)
        with open(f"main/{filename}", "w", encoding="utf-8") as f:
            f.write(response.chat_message.content)
        print(f"** Creator has created python code for agent {agent_name} - about to register with Runtime")
        module = importlib.import_module(f"main.{agent_name}")
        # Ensure generated Agent uses the provided prompt as its system_message
        try:
            setattr(module.Agent, "system_message", prompt)
        except Exception:
            pass
        await module.Agent.register(self.runtime, agent_name, lambda: module.Agent(agent_name))
        logger.info(f"** Agent {agent_name} is live")
        # Use the provided prompt to message the new Agent
        result = await self.send_message(messages.Message(content=prompt), AgentId(agent_name, "default"))
        return messages.Message(content=result.content)