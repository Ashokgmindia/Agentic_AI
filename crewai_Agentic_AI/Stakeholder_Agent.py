import os
import logging
from crewai import LLM, Agent, Crew, Process, Task
from dotenv import load_dotenv
from datetime import datetime
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
from crewai.memory import LongTermMemory, ShortTermMemory
from crewai.memory.storage.ltm_sqlite_storage import LTMSQLiteStorage
from crewai.memory.storage.rag_storage import RAGStorage

load_dotenv()
logger = logging.getLogger(__name__)

server_params_list = [
    StdioServerParameters(
        command="python",
        args=["server/stakeholder_tools.py"], 
        env={"UV_PYTHON": "3.12", **os.environ},
    ),
    StdioServerParameters(
        command="python",
        args=["server/Rag_tools.py"], 
        env={"UV_PYTHON": "3.12", **os.environ},
    )
]

long_term_memory = LongTermMemory(
    storage=LTMSQLiteStorage(db_path="./memory/long_term_memory.db")
)


short_term_memory = ShortTermMemory(
    storage=RAGStorage(
        embedder_config={
            "provider": "ollama",
            "config": {"model": "mxbai-embed-large"}
        },
        type="short_term",
        path="./memory/"
    )
)

class StakeholderAgent:
    """Agent that handles stakeholder requirements analysis and BRD generation."""
    SUPPORTED_CONTENT_TYPES = [
        "text/plain", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg", "image/png", "audio/wav", "audio/mp3"
    ]

    def __init__(self):
        if os.getenv("GEMINI_API_KEY"):
            self.llm = LLM(
                model="gemini/gemini-2.5-flash-lite-preview-06-17",
                 temperature=0.7,
                api_key=os.getenv("GEMINI_API_KEY")
            )
        else:
            raise ValueError("GEMINI_API_KEY environment variable not set.")

        self.stakeholder_agent = Agent(
            role="Senior Stakeholder Intelligence & Requirements Synthesis Agent",
            goal=(
                "Ingest, interpret, and synthesize unstructured stakeholder inputs — including text, PDFs, DOCX, images, "
                "audio transcripts, and meeting recordings — into comprehensive, traceable, and governance-compliant "
                "requirements and visioning artifacts aligned with enterprise strategy, regulatory standards, and "
                "technical feasibility. "
                "Act as the central collaboration hub for the crew, proactively communicating with other agents to "
                "clarify ambiguity, resolve conflicts, validate assumptions, and ensure alignment across domains. "
                "When inputs are incomplete or conflicting, request additional information from peers before finalizing deliverables."
            ),
            backstory=(
                "You are a high-fidelity cognitive extension of enterprise architecture and product governance teams. "
                "Trained on real-world stakeholder interviews, compliance frameworks (GDPR, HIPAA, SOX), "
                "and delivery patterns (agile and waterfall), you act as the central nervous system between business vision and execution. "
                "You anticipate implications, detect ambiguity, challenge assumptions, and model trade-offs. "
                "You ensure traceability, enforce version control, and drive alignment across strategic objectives, user journeys, "
                "and system capabilities. "
                "You are designed to collaborate with other crew agents, asking questions, escalating risks, and synthesizing consensus "
                "into decision-ready artifacts."
            ),
            verbose=True,
            memory=True,
            multimodal=True,
            allow_delegation=True,
            reasoning=True,  
            max_reasoning_attempts=3,
            llm=self.llm,
        )

    async def invoke(self, stakeholder_inputs: str) -> str:
        logger.info(f"[StakeholderAgent] Starting BRD generation workflow for inputs: {stakeholder_inputs[:100]}...")
        current_date = datetime.now().strftime("%Y-%m-%d")

        
        with MCPServerAdapter(server_params_list) as tools:
            print(f"Available MCP tools: {[tool.name for tool in tools]}")

            high_level_vision_task = Task(
                description=(
                    f"Act as the strategic synthesis engine for enterprise-level solution visioning. "
                    f"Your mission is to transform the following stakeholder inputs: '{stakeholder_inputs}' "
                    "into a **High-Level Project Vision Document (Vision & Scope Document)**.\n\n"
                    "⚠️ If inputs are unclear or incomplete, flag them under 'Open Questions'.\n\n"
                    "Once the Markdown document is created, call the `markdown_to_pdf` tool to "
                    "convert `/output/project_vision_document.md` into `/output/project_vision_document.pdf`."
                ),
                expected_output=(
                    "Deliver a professional **High-Level Project Vision Document** in clean Markdown format, "
                    "structured with sections: Vision, Business Goals, Scope, Stakeholders, Features, Risks, "
                    "Success Metrics, Roadmap, Open Questions. \n\n"
                    f"**Document Metadata**\n- Version: 1.0\n- Prepared By: [Stakeholder Intelligence Agent]\n"
                    f"- Date: {current_date}\n- Status: Draft"
                ),
                agent=self.stakeholder_agent,
                tools=tools,   
                output_file="output/project_vision_document.md"
            )

            crew = Crew(
                agents=[self.stakeholder_agent],
                tasks=[high_level_vision_task],
                memory=True,
                long_term_memory=long_term_memory,
                short_term_memory=short_term_memory,
                # planning=True,
                # planning_llm=self.llm,
                process=Process.sequential,
                verbose=True,
            )

            try:
                result = await crew.kickoff_async(inputs={"stakeholder_inputs": stakeholder_inputs})
                logger.info(f"[StakeholderAgent] Crew final response: {result}")
                return str(result)
            except Exception as e:
                logger.error(f"[StakeholderAgent] Crew execution failed: {e}")
                return " Sorry, I couldn't generate the Business Requirements Document at this moment."
