import os
import sys
import asyncio

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime
from autogen_core import AgentId

from main import messages
from main.creator import Creator
from main.upload_to_gcp import upload_to_gcp

HOW_MANY_AGENTS = 10

async def create_and_message(worker, creator_id, i: int):
    try:
        result = await worker.send_message(messages.Message(content=f"agent{i}.py"), creator_id)
        with open(f"ideas/idea{i}.md", "w") as f:
            f.write(result.content)
    except Exception as e:
        print(f"Failed to run worker {i} due to exception: {e}")

async def main():
    host = GrpcWorkerAgentRuntimeHost(address="localhost:50051")
    host.start() 
    worker = GrpcWorkerAgentRuntime(host_address="localhost:50051")
    await worker.start()
    result = await Creator.register(worker, "Creator", lambda: Creator("Creator"))
    creator_id = AgentId("Creator", "default")
    coroutines = [create_and_message(worker, creator_id, i) for i in range(1, HOW_MANY_AGENTS+1)]
    await asyncio.gather(*coroutines)
    try:
        await worker.stop()
        await host.stop()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    asyncio.run(main())
    signed_url = upload_to_gcp()
    print(signed_url)

