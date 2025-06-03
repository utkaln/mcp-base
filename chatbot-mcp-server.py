import os
import json
from typing import List
from dotenv import load_dotenv
import anthropic
import arxiv 
from mcp.server.fastmcp import FastMCP


RESEARCH_DIR = "research"

# Initialize the MCP server
mcp = FastMCP("research_mcp_server")


@mcp.tool()
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

@mcp.tool()
def extract_research_info(research_doc_id: str) -> str:
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
    



if __name__ == "__main__":
    mcp.run(transport="stdio")


# Instructions to run the server from terminal
# run ->  npx @modelcontextprotocol/inspector uv run chatbot-mcp-server.py
# Open browser and go to : http://127.0.0.1:6274 