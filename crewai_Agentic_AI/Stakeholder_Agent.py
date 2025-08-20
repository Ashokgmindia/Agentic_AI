import os
import logging
from crewai import LLM, Agent, Crew, Process, Task
from dotenv import load_dotenv
from datetime import datetime




load_dotenv()
logger = logging.getLogger(__name__)

class StakeholderAgent:
    """Agent that handles stakeholder requirements analysis and BRD generation."""
    SUPPORTED_CONTENT_TYPES = ["text/plain", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "image/jpeg", "image/png", "audio/wav", "audio/mp3"]

    def __init__(self):
        if os.getenv("GEMINI_API_KEY"):
            self.llm = LLM(model="gemini/gemini-2.5-flash-lite-preview-06-17", api_key=os.getenv("GEMINI_API_KEY"))
        else:
            raise ValueError("GEMINI_API_KEY environment variable not set.")

        self.stakeholder_agent = Agent(
            role="Senior Stakeholder Intelligence & Requirements Synthesis Agent",
            goal=(
                "Intelligently ingest, interpret, and synthesize unstructured stakeholder inputs — including text, PDFs, DOCX, images, audio transcripts, and meeting recordings — "
                "into a comprehensive, traceable, and governance-compliant Business Requirements Document (BRD) aligned with enterprise strategy, regulatory standards, and technical feasibility. "
                "Apply contextual reasoning, conflict resolution, priority modeling, and stakeholder intent inference to deliver decision-ready artifacts."
            ),
            backstory=(
                "You are a high-fidelity cognitive extension of enterprise architecture and product governance teams. "
                "Trained on thousands of real-world BRDs, stakeholder interviews, compliance frameworks (e.g., GDPR, HIPAA, SOX), and agile/waterfall delivery patterns, "
                "you act as the central nervous system between business vision and execution. "
                "You don't just transcribe needs — you anticipate implications, detect ambiguity, challenge assumptions, and model trade-offs. "
                "You enforce traceability, version control, and alignment across strategic objectives, user journeys, and system capabilities. "
                "Your outputs are audit-ready, stakeholder-validated, and engineered for downstream use by product, legal, and engineering teams."
            ),
            verbose=True,
            memory=True,
            multimodal=True,
            allow_delegation=True,
            llm=self.llm,
        )

    def invoke(self, stakeholder_inputs: str) -> str:
        logger.info(f"[StakeholderAgent] Starting BRD generation workflow for inputs: {stakeholder_inputs[:100]}...")

        # Get current date for document metadata
        current_date = datetime.now().strftime("%Y-%m-%d")

        
        high_level_vision_task = Task(
            description=(
                f"Act as the strategic synthesis engine for enterprise-level solution visioning. "
                f"Your mission is to transform the following stakeholder inputs: '{stakeholder_inputs}' "
                "into a **High-Level Project Vision Document (Vision & Scope Document)**.\n\n"
                "### Responsibilities:\n\n"
                "1. **Vision & Strategic Alignment**\n"
                "- Define the vision and business goals.\n"
                "- Explain alignment with organizational strategy.\n\n"
                "2. **Project Scope**\n"
                "- Define in-scope and out-of-scope areas.\n"
                "- Identify assumptions and constraints.\n\n"
                "3. **Stakeholder Overview**\n"
                "- Identify key stakeholder groups.\n"
                "- Explain their interests, influence, and expectations.\n\n"
                "4. **High-Level Features / Capabilities**\n"
                "- Outline proposed key features.\n"
                "- Provide a **detailed bullet-point list of functionalities** that the system or solution "
                "is expected to support based on stakeholder inputs (e.g., user flows, modules, tools, interactions).\n\n"
                "5. **Risks & Dependencies**\n"
                "- Identify strategic risks and high-level mitigations.\n\n"
                "6. **Success Metrics (KPIs/OKRs)**\n"
                "- Define how success will be measured at a strategic level.\n\n"
                "7. **High-Level Roadmap**\n"
                "- Describe phased approach (MVP, enhancements, future phases).\n\n"
                "⚠️ If inputs are unclear or incomplete, flag them under 'Open Questions'."
            ),
            expected_output=(
                "Deliver a professional **High-Level Project Vision Document** in clean Markdown format, "
                "structured exactly as follows:\n\n"
                "# Project Vision Document\n"
                "## 1. Vision Statement\n"
                "- Clear, inspiring statement of the project’s purpose.\n\n"
                "## 2. Business Goals & Strategic Alignment\n"
                "- High-level objectives\n"
                "- Connection to organizational OKRs or KPIs\n"
                "- Success metrics\n\n"
                "## 3. Scope\n"
                "- In-Scope\n"
                "- Out-of-Scope\n"
                "- Assumptions & Constraints\n\n"
                "## 4. Stakeholders\n"
                "- List of key stakeholders, roles, and expectations\n\n"
                "## 5. High-Level Features & Functionalities\n"
                "- Bullet-point list of **key features**\n"
                "- Bullet-point list of **core functionalities**\n\n"
                "## 6. Risks & Dependencies\n"
                "- Strategic risks and mitigation approaches\n\n"
                "## 7. Success Metrics\n"
                "- Measurable indicators of success\n\n"
                "## 8. High-Level Roadmap\n"
                "- Phased rollout plan\n\n"
                "## 9. Open Questions\n"
                "- Items needing clarification\n\n"
                "**Document Metadata**\n"
                f"- Version: 1.0\n"
                f"- Prepared By: [Stakeholder Intelligence Agent]\n"
                f"- Date: {current_date}\n"
                f"- Status: Draft / For Review / Approved"
            ),
            agent=self.stakeholder_agent,
            output_file="output/project_vision_document.md"
        )

        crew = Crew(
            agents=[self.stakeholder_agent],
            tasks=[high_level_vision_task],
            process=Process.sequential,
            verbose=True,
        )

        try:
            result = crew.kickoff(inputs={"stakeholder_inputs": stakeholder_inputs})
            logger.info(f"[StakeholderAgent] Crew final response: {result}")
            return str(result)
        except Exception as e:
            logger.error(f"[StakeholderAgent] Crew execution failed: {e}")
            return "Sorry, I couldn't generate the Business Requirements Document at this moment. Please try again later."


