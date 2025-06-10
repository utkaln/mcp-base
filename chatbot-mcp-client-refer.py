import os
import json
from typing import List, Dict, TypedDict
from dotenv import load_dotenv, find_dotenv
import anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
from contextlib import AsyncExitStack

# nest asyncio is used to allow looping of events with async calls. 
# This avoids the runtime error: "This event loop is already running"
import nest_asyncio
nest_asyncio.apply()
_ = load_dotenv(find_dotenv())

class ToolDefinition(TypedDict):
    name: str
    description: str
    input_schema : dict 


class McpChatbotClient:
    def __init__(self):
        # maintain collection of sessions that the client is connected to
        self.session: List[ClientSession] = []
        self.llm = anthropic.Anthropic()
        self.tools: List[ToolDefinition] = []
        self.tool_to_session: Dict[str, ClientSession] = {}
        self.available_tools: List[ToolDefinition] = []
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_name: str, server_config: dict ) -> None:
        """ Connect to a single MCP Server """
        try:
            # Create server parameters for stdio connection
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.session.append(session)
            response = await session.list_tools()
            tools = response.tools
            print(f"\nConnected to {server_name} with tools:", [tool.name for tool in tools])

            for tool in tools:
                self.tool_to_session[tool.name] = session
                self.available_tools.append(
                    {
                        "name" : tool.name,
                        "description" : tool.description,
                        "input_schema" : tool.inputSchema
                    }
                )

        except Exception as e:
                print(f"Error connecting to server {server_name}: {e}")
    
    async def connect_to_servers(self):
        """ Connect to all MCP servers defined in server_config.json file """
        try:
            with open("server_config.json", "r") as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server configuration: {e}")
            raise    
    
    # Process Query using LLM
    async def process_query(self, query):
        messages = [{'role': 'user', 'content': query}]
        response = self.llm.messages.create(
            max_tokens=2048,
            model='claude-3-7-sonnet-20250219',
            tools=self.tools,
            messages=messages
        )

        continue_processing = True
        while continue_processing:
            assistant_content = []
            for content in response.content:
                if content.type == 'text':
                    print(f"Text returned from LLM Search -> {content.text}")
                    assistant_content.append(content)

                    # return of response from llm is finished
                    if len(response.content) == 1:
                        continue_processing = False
                
                elif content.type == 'tool_use':
                    assistant_content.append(content)
                    messages.append({'role':'assistant', 'content': assistant_content})

                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name
                    print(f"Calling tool: {tool_name} with arguments: {tool_args}")

                    # Call Tool 
                    session = self.tool_to_session[tool_name]
                    result = session.call_tool(tool_name,arguments=tool_args)
                    messages.append({'role':'user', 'content':[
                        {
                            'type': 'tool_result',
                            'tool_use_id': tool_id,
                            'content': result.content
                        }
                    ]})


                    # Send the output of tool back to LLM for summarization
                    response = self.llm.messages.create(
                        max_tokens=2048,
                        model='claude-3-7-sonnet-20250219',
                        messages= messages,
                        tools= self.tools
                    )

                    if len(response.content) == 1 and response.content[0].type == 'text':
                        print(f"Final Response -> {response.content[0].text}")
                        continue_processing = False

    async def chat_loop(self):
        """ Run an interactive chat loop with the user until the user types 'quit' """
        print("Welcome to the Research Chatbot!")
        print("Type 'quit' to quit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                await self.process_query(query)
            except Exception as e:
                print(f"An error occurred: {e}")

    async def cleanup(self):
        """ Cleanly close all resources using AsyncExitStack """
        await self.exit_stack.aclose()
             

async def main():
    chatbot = McpChatbotClient()
    try:
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

        
