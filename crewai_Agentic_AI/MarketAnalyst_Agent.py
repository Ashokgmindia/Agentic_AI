import os
import logging
from crewai import LLM, Agent, Crew, Process, Task
from dotenv import load_dotenv
from datetime import datetime
from typing import Union, List
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

server_params_list = [
    StdioServerParameters(
        command="python",
        args=["server/search_tools.py"], 
        env={"UV_PYTHON": "3.12", **os.environ},
    )
    # StdioServerParameters(
    #     command="python",
    #     args=["server/Rag_tools.py"], 
    #     env={"UV_PYTHON": "3.12", **os.environ},
    # )
]

load_dotenv()
logger = logging.getLogger(__name__)


class MarketAnalystAgent:
    """Agent that performs advanced market analysis based on stakeholder inputs."""

    def __init__(self):
        # Choose LLM depending on available API key
        if os.getenv("GEMINI_API_KEY"):
            self.llm = LLM(model="gemini/gemini-2.5-flash-lite-preview-06-17", api_key=os.getenv("GEMINI_API_KEY"))
        elif os.getenv("OPENAI_API_KEY"):
            self.llm = LLM(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
        else:
            raise ValueError("Neither GEMINI_API_KEY nor OPENAI_API_KEY environment variable is set.")

        # Define the Market Analyst Agent
        self.market_analyst = Agent(
            role="Market Research Analyst",
            goal=(
                "Perform complete market analysis that transforms stakeholder input "
                "into strategic insights for decision making."
            ),
            backstory=(
                "With years of experience in business intelligence, you specialize in "
                "uncovering opportunities and risks in dynamic markets. You excel at "
                "turning stakeholder needs into actionable market insights."
            ),
            verbose=True,
            memory=True,
            allow_delegation=True,
            llm=self.llm,
        )

    async def invoke(self, stakeholder_input: Union[str, List[str]]) -> str:
        """
        Run the market analysis task using the stakeholder input provided.
        """
        logger.info("[MarketAnalystAgent] Starting market analysis...")

        current_date = datetime.now().strftime("%Y-%m-%d")


        # with MCPServerAdapter(server_params_list) as tools:
        #             print(f"Available MCP tools: {[tool.name for tool in tools]}")

        

        with MCPServerAdapter(server_params_list) as tools:
        
          logger.info(f"Available MCP tools: {[tool.name for tool in tools]}")

        market_analysis_task = Task(
            description=(
                "Conduct a comprehensive market analysis based on the provided stakeholder input. "
                "Follow these steps:\n\n"
                "1. Review stakeholder requirements.\n"
                "2. Use the **web_search** tool to find and profile relevant competitors.\n"
                "3. Use the **web_search** tool to analyze market trends, regulations, and consumer behavior.\n"
                "4. Assess risks and opportunities with the data collected.\n"
                "5. Compile findings into a structured final report.\n\n"
                f"Stakeholder Input: {stakeholder_input}"
            ),
            expected_output=(
                "Final deliverable MUST be a structured market research report with:\n"
                "- Stakeholder Requirements\n"
                "- Competitor Profiles (with references)\n"
                "- Market Trends (latest data)\n"
                "- Risks & Opportunities\n"
                "- Final Recommendations\n\n"
                f"- Prepared By: Market Analyst Agent\n- Date: {current_date}"
            ),
            agent=self.market_analyst,
            tools=tools,   
            output_file="output/market_analysis_report.md"
        )

        crew = Crew(
            agents=[self.market_analyst],
            tasks=[market_analysis_task],
            process=Process.sequential,
            verbose=True,
        )

        try:
            result = await crew.kickoff_async(inputs={"stakeholder_input": stakeholder_input})
            logger.info(f"[MarketAnalystAgent] Crew final response: {result}")
            return str(result)
        except Exception as e:
            logger.error(f"[MarketAnalystAgent] Crew execution failed: {e}")
            return "Sorry, I couldn't generate the Market Analysis Report at this moment. Please try again later."

    
