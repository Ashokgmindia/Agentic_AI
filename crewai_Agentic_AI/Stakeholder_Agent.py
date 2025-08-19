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
            allow_delegation=False,
            llm=self.llm,
        )

    def invoke(self, stakeholder_inputs: str) -> str:
        logger.info(f"[StakeholderAgent] Starting BRD generation workflow for inputs: {stakeholder_inputs[:100]}...")

        # Get current date for document metadata
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Create the requirements synthesis task
        strategic_requirements_synthesis_task = Task(
            description=(
                f"Act as the principal requirements intelligence engine for enterprise-level solution design. "
                f"Your mission is to ingest, analyze, and synthesize the following stakeholder inputs: '{stakeholder_inputs}' "
                "into a precise, strategic, and audit-ready Business Requirements Document (BRD).\n\n"
                "You operate at the intersection of business strategy, technical feasibility, and regulatory compliance. "
                "Do not merely transcribe inputs—interpret intent, detect ambiguity, resolve contradictions, and infer implicit needs using contextual reasoning and industry best practices.\n\n"
                "### Core Responsibilities:\n\n"
                "1. **Intelligent Requirement Extraction & Structuring**\n"
                "- Parse all provided inputs (including non-textual) to identify functional, non-functional, compliance, and strategic requirements.\n"
                "- Assign unique, traceable IDs (e.g., REQ-FUNC-001, REQ-COMPL-002) to each requirement.\n"
                "- Convert vague ideas into SMART (Specific, Measurable, Achievable, Relevant, Time-bound) requirements.\n"
                "- Clarify ambiguous statements by inferring intent based on context and stakeholder role.\n\n"
                "2. **Stakeholder Alignment & Conflict Resolution**\n"
                "- Map each requirement to its originating stakeholder or artifact (e.g., 'Marketing Team - Q3 Strategy Deck').\n"
                "- Identify conflicts (e.g., UX vs. Security, Cost vs. Scalability) and propose data-driven resolutions.\n"
                "- Apply prioritization frameworks (MoSCoW or Value vs. Effort) unless otherwise specified.\n"
                "- Align every requirement with measurable business outcomes (KPIs, OKRs, ROI).\n\n"
                "3. **Risk, Compliance & Change Impact Analysis**\n"
                "- Flag regulatory risks (e.g., GDPR, HIPAA, SOC2) associated with requirements.\n"
                "- Assess technical feasibility and operational impact.\n"
                "- Highlight potential scope creep and recommend change control measures.\n"
                "- Propose mitigation strategies for high-risk items.\n\n"
                "4. **Governance & Audit Readiness**\n"
                "- Ensure full bidirectional traceability: from source input → requirement → business goal → acceptance criteria.\n"
                "- Define clear, testable acceptance criteria for every requirement.\n"
                "- Include version metadata, authorship, and review status.\n"
                "- Generate a formal approval checklist for stakeholder sign-off.\n\n"
                "⚠️ If any input is incomplete, contradictory, or lacks sufficient detail for confident interpretation, "
                "explicitly flag it under 'Assumptions & Open Questions' and suggest follow-up actions."
            ),
            expected_output=(
                "Deliver a comprehensive, professional **Business Requirements Document (BRD)** in clean Markdown format, "
                "structured exactly as follows. The document must be self-contained, logically organized, and ready for review by product, legal, engineering, and executive teams.\n\n"
                "# Business Requirements Document (BRD)\n"
                "## 1. Introduction\n"
                "- Purpose of the document\n"
                "- Project overview\n"
                "- Key stakeholders and roles\n\n"
                "## 2. Business Goals & Strategic Alignment\n"
                "- High-level objectives\n"
                "- Connection to organizational OKRs or KPIs\n"
                "- Success metrics\n\n"
                "## 3. Consolidated Stakeholder Requirements\n"
                "| Req ID | Description | Priority (High/Med/Low) | Source | Business Goal Alignment | Acceptance Criteria |\n"
                "|--------|-------------|-------------------------|--------|--------------------------|----------------------|\n"
                "| REQ-FUNC-001 | [Clear, testable description] | High | [e.g., CTO Interview - 2025-04-01] | [e.g., Improve customer retention] | [e.g., 95% success rate in UAT] |\n"
                "... additional rows ...\n\n"
                "## 4. Conflicting Requirements & Resolutions\n"
                "- List all identified conflicts\n"
                "- Describe root cause\n"
                "- Provide recommended resolution and rationale\n\n"
                "## 5. Risks & Mitigation Strategies\n"
                "- Technical, operational, compliance, and timeline risks\n"
                "- Likelihood & impact assessment\n"
                "- Recommended actions and ownership suggestions\n\n"
                "## 6. Compliance & Governance Considerations\n"
                "- Applicable regulations (e.g., GDPR, CCPA)\n"
                "- Data privacy, security, and audit implications\n"
                "- Required controls or documentation\n\n"
                "## 7. Assumptions & Open Questions\n"
                "- List all assumptions made during analysis\n"
                "- Highlight unresolved items needing clarification\n\n"
                "## 8. Final Approval Checklist\n"
                "- [ ] Business Owner Sign-off\n"
                "- [ ] Technical Lead Review\n"
                "- [ ] Legal/Compliance Acknowledgment\n"
                "- [ ] Project Sponsor Approval\n"
                "- [ ] Version Control & Archive Confirmation\n\n"
                "**Document Metadata**\n"
                f"- Version: 1.0\n"
                f"- Prepared By: [Stakeholder Intelligence Agent]\n"
                f"- Date: {current_date}\n"
                f"- Status: Draft / For Review / Approved"
            ),
            agent=self.stakeholder_agent,
            # tools=[markdown_to_pdf],
            output_file="output/stakeholder_document.md"
        )

        crew = Crew(
            agents=[self.stakeholder_agent],
            tasks=[strategic_requirements_synthesis_task],
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


