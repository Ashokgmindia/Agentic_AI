import os
import warnings
from dotenv import load_dotenv
from crewai_tools import SerperDevTool
from mcp.server.fastmcp import FastMCP


warnings.filterwarnings("ignore")


load_dotenv()

mcp = FastMCP("search_tools")


search_tool = SerperDevTool()

@mcp.tool()
async def web_search(query: str) -> str:
    """
    Perform a web search using the Serper API.

    Args:
        query (str): The search query.

    Returns:
        str: Search results or an error message.
    """
    try:
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            return "Error: SERPER_API_KEY environment variable not set."

        # ✅ Use async version of SerperDevTool
        result = await search_tool.run(query=query)
        return str(result)

    except Exception as e:
        return f"Error running search: {e}"

if __name__ == "__main__":
   
    mcp.run(transport="stdio")





