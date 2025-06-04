import os
import json
from typing import List
from dotenv import load_dotenv, find_dotenv
import anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio

# nest asyncio is used to allow looping of events with async calls. 
# This avoids the runtime error: "This event loop is already running"
import nest_asyncio
nest_asyncio.apply()
_ = load_dotenv(find_dotenv())


class McpChatbotClient:
    def __init__(self):
        # these initial values will change once the client is connected to the server
        self.session: ClientSession = None
        self.llm = anthropic.Anthropic()
        self.tools: List[dict] = []

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

                    result = self.session.call_tool(tool_name,arguments=tool_args)
                    messages.append({'role':'user', 'content':[
                        {
                            'type': 'tool_result',
                            'tool_use_id': tool_id,
                            'content': result
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


    async def connect_to_server_and_run(self):
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command="uv",  # Executable
            args=["run", "chatbot-mcp-server.py"],  # Optional command line arguments
            env=None,  # Optional environment variables
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                # Initialize the connection
                await session.initialize()
    
                # List available tools
                response = await session.list_tools()
                
                tools = response.tools
                print("\nConnected to server with tools:", [tool.name for tool in tools])
                
                self.available_tools = [{
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                } for tool in response.tools]
    
                await self.chat_loop()

async def main():
    chatbot = McpChatbotClient()
    await chatbot.connect_to_server_and_run()

if __name__ == "__main__":
    asyncio.run(main())

        
