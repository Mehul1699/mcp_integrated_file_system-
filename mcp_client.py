import asyncio
import sys
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

# -----------------------------------------
# Configuration
# -----------------------------------------

BASE_DIR = Path(__file__).resolve().parent
SERVER_PATH = BASE_DIR / "filesystem_mcp_server.py"

server_params = StdioServerParameters(
    command=sys.executable, args=[str(SERVER_PATH)], env=None
)


class MCPFilesystemClient:

    async def __aenter__(self):
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        self.session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await self.session.initialize()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def list_tools(self):
        return await self.session.list_tools()

    async def list_resources(self):
        return await self.session.list_resources()

    async def read_resource(self, uri):
        return await self.session.read_resource(uri)

    async def list_resumes(self, directory="", extension=None):
        arguments = {"directory": directory, "extension": extension}
        return await self.session.call_tool("list_resumes", arguments=arguments)

    async def read_resume(self, filepath):
        return await self.session.call_tool(
            "read_resume", arguments={"filepath": filepath}
        )

    async def search_resume(self, filepath, keyword):
        return await self.session.call_tool(
            "search_resume", arguments={"filepath": filepath, "keyword": keyword}
        )

    async def write_resume(self, filepath, content):
        return await self.session.call_tool(
            "write_resume", arguments={"filepath": filepath, "content": content}
        )

    async def batch_process(self, filepaths=None):
        arguments = {}
        if filepaths is not None:
            arguments["filepaths"] = filepaths

        return await self.session.call_tool("batch_process", arguments=arguments)

    async def watch_directory(self, duration_seconds=30, poll_interval=2):
        return await self.session.call_tool(
            "watch_directory",
            arguments={
                "duration_seconds": duration_seconds,
                "poll_interval": poll_interval,
            },
        )


# ------------------------------------------
# Standalone connection test
# ------------------------------------------


async def main():
    print


# ------------------------------------------
# MCP Client
# ------------------------------------------


async def main():
    print("Connecting to Filesystem MCP Server...")

    try:
        async with MCPFilesystemClient() as client:

            # Initialize MCP connection
            print("\nConnected successfully!")

            # -----------------------------------------
            # 1. Discover available MCP tools
            # -----------------------------------------

            print("\n--- AVAILABLE MCP TOOLS ---")

            tools = await client.list_tools()

            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            # -------------------------------------------
            # 2. Discover available resources
            # -------------------------------------------

            print("\n--- AVAILABLE MCP RESOURCES ---")

            resources = await client.list_resources()

            for resource in resources.resources:
                print(f"- {resource.name}: {resource.uri}")

            # ------------------------------------------
            # 3. Read a resource
            # ------------------------------------------

            print("\n--- RESUME DIRECTORY RESOURCE ---")

            directory = await client.read_resource("resumes://directory")

            for item in directory.contents:
                if hasattr(item, "text"):
                    print(item.text)

            # ------------------------------------------
            # 4. Batch process all resumes
            # ------------------------------------------

            print("\n--- BATCH PROCESS ALL RESUMES ---")

            result = await client.batch_process()

            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text)

            if result.isError:
                print("Batch processing returned an error.")
                return

            print("\nMCP client test completed.")

    except Exception as e:
        print(f"\nMCP Client Error: {e}")


# --------------------------------------------
# Run client
# --------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
