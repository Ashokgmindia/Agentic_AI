import os
import logging
from crewai import LLM, Agent, Crew, Process, Task
from dotenv import load_dotenv
from datetime import datetime
from typing import Union, List
# from Stakeholder_Agent import StakeholderAgent
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
# from Stakeholder_Agent import stakeholder_agent


load_dotenv()
logger = logging.getLogger(__name__)


# server_params_list = [
#     StdioServerParameters(
#         command="python",
#         args=["server/search_tools.py"], 
#         env={"UV_PYTHON": "3.12", **os.environ},
#     )
#     # StdioServerParameters(
#     #     command="python",
#     #     args=["server/Rag_tools.py"], 
#     #     env={"UV_PYTHON": "3.12", **os.environ},
#     # )
# ]


# server_params = StdioServerParameters(
#     command="python",
#     args=["server/search_tools.py"], 
#     env={"UV_PYTHON": "3.12", **os.environ},
# )


class BusinessAnalystAgent:
    """Multimodal Agent that performs requirement gathering and BRD/User Story generation."""

    SUPPORTED_CONTENT_TYPES = [
        "text/plain",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
        "audio/wav",
        "audio/mp3",
    ]

    def __init__(self):
        
        if os.getenv("GEMINI_API_KEY"):
            self.llm = LLM(model="gemini/gemini-2.5-flash-lite-preview-06-17", api_key=os.getenv("GEMINI_API_KEY"))
        elif os.getenv("OPENAI_API_KEY"):
            self.llm = LLM(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
        else:
            raise ValueError("Neither GEMINI_API_KEY nor OPENAI_API_KEY environment variable is set.")

        self.business_analyst = Agent(
            role="Senior Business Analyst & Strategic Advisor",
            goal=(
                "Drive business transformation by performing deep analysis of "
                "requirements, uncovering inefficiencies, and shaping actionable "
                "solutions that align with long-term organizational strategy. "
                "Ensure your insights empower decision-making and provide a "
                "strong foundation for execution by other agents."
            ),
            backstory=(
                "You are a seasoned Business Analyst with 20+ years of experience "
                "bridging the gap between business vision and technical delivery. "
                "Known for your ability to see the big picture while managing "
                "details, you specialize in uncovering hidden risks, identifying "
                "value opportunities, and ensuring that every requirement serves "
                "a clear business outcome. "
                "You thrive in collaborative environments where your structured "
                "thinking and strategic mindset elevate the contributions of others."
            ),
            verbose=True,
            memory=True,
            # multimodal=True,
            allow_delegation=True,
    
            llm=self.llm,
        )

    async def invoke(self, stakeholder_inputs: Union[str, List[str]]) -> str:
        """
        Accepts raw project context (str) OR a list of multimodal inputs (file paths, transcripts).
        """
        logger.info(f"[BusinessAnalystAgent] Starting multimodal requirements analysis...")

        current_date = datetime.now().strftime("%Y-%m-%d")
        # with MCPServerAdapter(server_params) as tools:
        #     print(f"Available MCP tools: {[tool.name for tool in tools]}")

        business_requirements_analysis_task = Task(
            description=(
                "This is a two-phase task requiring advanced business analysis expertise:\n\n"
                "🔹 **Phase 1: Stakeholder Input Analysis**\n"
                "- Perform a structured and critical analysis of the provided stakeholder inputs.\n"
                "- Use advanced techniques such as SWOT analysis, PESTLE assessment, stakeholder influence mapping, "
                "and regulatory/compliance impact evaluation.\n"
                "- Identify conflicts, trade-offs, hidden assumptions, and alignment gaps across stakeholders.\n"
                "- Summarize key business drivers, risks, and success enablers.\n\n"
                "🔹 **Phase 2: BRD Creation**\n"
                "- Based on the insights from Phase 1, craft an enterprise-grade Business Requirements Document (BRD) "
                "for the strategic digital transformation project: development of an AI-driven global e-commerce platform.\n"
                "- Ensure the document is tailored to inform and persuade executives, investors, project managers, "
                "and solution architects, serving as the authoritative reference.\n"
                "- Connect corporate vision to functional and technical requirements, ensure compliance with "
                "data privacy and international regulations, and emphasize financial/operational implications.\n\n"
                f"Inputs provided: {stakeholder_inputs}"
            ),
            expected_output=(
                "Your final deliverable MUST include two comprehensive sections:\n\n"
                "### 1. Advanced Stakeholder Input Analysis\n"
                "- Stakeholder matrix (influence vs. interest)\n"
                "- SWOT and/or PESTLE analysis of the project context\n"
                "- Identification of competing priorities, conflicts, and trade-offs\n"
                "- Key business drivers, risks, enablers, and regulatory considerations\n\n"
                "### 2. Formal Business Requirements Document (BRD)\n"
                "1. Executive Vision & Strategic Alignment\n"
                "   - Business case, objectives, and value proposition\n"
                "   - Alignment with corporate mission and long-term strategy\n\n"
                "2. Market & Competitive Landscape\n"
                "   - Benchmarking, trends, and opportunities\n"
                "   - Differentiation factors and positioning\n\n"
                "3. Project Scope & Boundaries\n"
                "   - In-scope, out-of-scope, dependencies, and exclusions\n\n"
                "4. Stakeholder & Governance Model\n"
                "   - Governance structure and RACI matrix\n"
                "   - Escalation paths and decision-making protocols\n\n"
                "5. Detailed Business Requirements\n"
                "   - Functional, non-functional, regulatory requirements\n"
                "   - Prioritization matrix (Must/Should/Could/Won’t)\n\n"
                "6. Current vs. Future State Blueprint\n"
                "   - As-Is vs. To-Be workflows, supported by diagrams\n"
                "   - Gap analysis and phased transformation roadmap\n\n"
                "7. Risk & Compliance Considerations\n"
                "   - Risk register with likelihood/impact scoring\n"
                "   - Data privacy, cybersecurity, and regulatory obligations\n\n"
                "8. Financial & ROI Analysis\n"
                "   - High-level cost models, CAPEX vs. OPEX\n"
                "   - ROI projections, break-even timeline, and sensitivity analysis\n\n"
                "9. Success Metrics & KPIs\n"
                "   - Leading and lagging indicators tied to business outcomes\n"
                "   - Metrics for adoption, performance, and financial impact\n\n"
                "10. Appendices\n"
                "   - Glossary, reference models, raw stakeholder input mapping\n\n"
                "### Document Metadata\n"
                f"- Prepared By: Business Analyst Agent\n- Date: {current_date}"
                " - use the MCP tool for web_search"
            ),
            agent=self.business_analyst,
            #  tools=tools,
              
            output_file="output/business_requirements_document.md"
           
        )


        crew = Crew(
            agents=[self.business_analyst],
            tasks=[business_requirements_analysis_task],
            process=Process.sequential,
            verbose=True,
        )

        try:
            result = await crew.kickoff_async(inputs={"stakeholder_inputs": stakeholder_inputs})
            logger.info(f"[BusinessAnalystAgent] Crew final response: {result}")
            return str(result)
        except Exception as e:
            logger.error(f"[BusinessAnalystAgent] Crew execution failed: {e}")
            return "Sorry, I couldn't generate the Business Requirements Document at this moment. Please try again later."
        
    def finalize(self, draft_output: str, human_feedback: str = "ok") -> str:
            """Commit output only if human validates it, otherwise refine."""
            if human_feedback.lower() == "ok":
                with open("output/business_requirements_document.md", "w", encoding="utf-8") as f:
                    f.write(draft_output)
                logger.info("[BusinessAnalystAgent] Final BRD saved after human approval.")
                return "Final BRD saved successfully."
            else:
                logger.info(f"[BusinessAnalystAgent] Re-running with human feedback: {human_feedback}")
                # Here you could call self.invoke again with stakeholder_inputs + feedback
                return f"Feedback received, please re-run with context: {human_feedback}"
