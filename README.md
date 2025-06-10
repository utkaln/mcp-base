# mcp-base

## Resource Reference
- [Anthropic MCP Servers](https://github.com/modelcontextprotocol/servers)

## Run MCP Server Locally for stdio

- Install dependencies

```sh
uv init
uv add -r requirements.txt
@modelcontextprotocol/inspector uv run chatbot-mcp-server.py
```
- Open browser and go to : http://127.0.0.1:6274 


## Run MCP client locally for stdio
- activate virtual environment and add dependency libraries

```sh
source .venv/bin/activate
uv add anthropic python_dotenv nest_asyncio
uv run chatbot-mcp-client.py
```


### Download and Run Reference servers
- Refer to the repo: https://github.com/modelcontextprotocol/servers
- Build a server-config.json to define reference server details
- Please note that `uvx` for python and `npx` for typescript is used to locally download and run the mcp servers
