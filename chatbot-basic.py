import os
import json
from typing import List
from dotenv import load_dotenv
import anthropic
import arxiv 

RESEARCH_DIR = "research"



# Search for research paper metadata
def search_research_papers(topic:str, max_results:int = 5) -> List[str]:
    """
    Search for papers on arXiv based on a topic and store their information.
    
    Args:
        topic: The topic to search for
        max_results: Maximum number of results to retrieve (default: 5)
        
    Returns:
        List of paper IDs found in the search
    """

    research_client = arxiv.Client()
    search = arxiv.Search(
        query = topic,
        max_results = max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )

    # Create directory for this topic
    path = os.path.join(RESEARCH_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)

    file_path = os.path.join(path, "papers_info.json")


    results = research_client.results(search)
    research_paper_ids = []
    research_dict = {}
    for doc in results:
        research_paper_ids.append(doc.get_short_id())
        research_paper_info = {
            'title': doc.title,
            'summary': doc.summary,
            'authors': [author.name for author in doc.authors],
            'pdf_url': doc.pdf_url,
            'published': str(doc.published.date()),
        }
        research_dict[doc.get_short_id()] = research_paper_info

    # Create directory for this topic
    path = os.path.join(RESEARCH_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)
    
    file_path = os.path.join(path, "papers_info.json")

    # Save updated papers_info to json file
    with open(file_path, "w") as json_file:
        json.dump(research_dict, json_file, indent=2)
    
    print(f"Results are saved in: {file_path}")
    
    return research_paper_ids


def extract_research_info(research_doc_id: int) -> str:
    """
    Search for information about a specific paper across all topic directories.
    
    Args:
        research_doc_id: The ID of the paper to look for
        
    Returns:
        JSON string with paper information if found, error message if not found
    """
    
    for item in os.listdir(RESEARCH_DIR):
        item_path = os.path.join(RESEARCH_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                        if research_doc_id in papers_info:
                            return json.dumps(papers_info[research_doc_id], indent=2)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue
    
    return f"Paper with ID {research_doc_id} not found in any topic directory."
                    

# search_research_papers("artificial intelligence", 5)
# print(extract_research_info("1509.01213v1"))

# Define Tool Schema
tools = [
    {
        "name": "search_research_papers",
        "description": "Search for research papers on a specific topic and store their information.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic to search for.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to retrieve (default: 5).",
                },
            },
            "required": ["topic"],
        },
    },
    {
        "name": "extract_research_info",
        "description": "Extract information about a specific research paper by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "research_doc_id": {
                    "type": "string",
                    "description": "The ID of the research paper to look for.",
                },
            },
            "required": ["research_doc_id"],
        },
    }
]

# Create Tool Mapping
mapping_tool_functions = {
    "search_research_papers": search_research_papers,
    "extract_research_info": extract_research_info,
}

def execute_tool(tool_name, tool_args):
    result = mapping_tool_functions[tool_name](**tool_args)

    if result is None:
        result = "The operation completed but didn't return any results."
        
    elif isinstance(result, list):
        result = ', '.join(result)
        
    elif isinstance(result, dict):
        # Convert dictionaries to formatted JSON strings
        result = json.dumps(result, indent=2)
    
    else:
        # For any other type, convert using str()
        result = str(result)
    return result


# Invoke Chatbot call
load_dotenv()
llm_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

# Process Query using LLM
def process_query(query):
    messages = [{'role': 'user', 'content': query}]
    response = llm_client.messages.create(
        max_tokens=2048,
        model='claude-3-7-sonnet-20250219',
        tools=tools,
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
                print(f"Tool suggested from LLM Search -> {content.text}")
                assistant_content.append(content)
                messages.append({'role':'assistant', 'content': assistant_content})

                tool_id = content.id
                tool_args = content.input
                tool_name = content.name
                print(f"Calling tool: {tool_name} with arguments: {tool_args}")

                result = execute_tool(tool_name, tool_args)
                messages.append({'role':'user', 'content':[
                    {
                        'type': 'tool_result',
                        'tool_user_id': tool_id,
                        'content': result
                    }
                ]})


                # Send the output of tool back to LLM for summarization
                response = llm_client.messages.create(
                    max_tokens=2048,
                    model='claude-3-7-sonnet-20250219',
                    messages= messages,
                    tools= tools

                )

                if len(response.content) == 1 and response.content[0].type == 'text':
                    print(f"Final Response -> {response.content[0].text}")
                    continue_processing = False


# Create a loop for conversation with user to continue
def chat_loop():
    print("Welcome to the Research Chatbot!")
    print("Type 'exit' to quit.")
    
    while True:
        try:
            query = input("\nQuery: ").strip()
            if query.lower() == 'quit':
                break
            process_query(query)
        except Exception as e:
            print(f"An error occurred: {str(e)}")



# Invoke the chat loop
chat_loop()

        
