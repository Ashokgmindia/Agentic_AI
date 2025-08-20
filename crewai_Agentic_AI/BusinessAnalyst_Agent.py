import os
import logging
from crewai import LLM, Agent, Crew, Process, Task
from dotenv import load_dotenv
from datetime import datetime
from typing import Union, List

load_dotenv()
logger = logging.getLogger(__name__)

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
        # Load LLM (example with Gemini, can swap to OpenAI multimodal if preferred)
        if os.getenv("GEMINI_API_KEY"):
            self.llm = LLM(model="gemini/gemini-2.5-flash-lite-preview-06-17", api_key=os.getenv("GEMINI_API_KEY"))
        elif os.getenv("OPENAI_API_KEY"):
            self.llm = LLM(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
        else:
            raise ValueError("Neither GEMINI_API_KEY nor OPENAI_API_KEY environment variable is set.")

        self.business_analyst = Agent(
            role="Multimodal Business Analyst",
            goal=(
                "Ingest and analyze multimodal stakeholder inputs — including text, PDFs, "
                "Word docs, images, and audio transcripts — to synthesize them into a "
                "structured, traceable, and actionable set of business requirements."
            ),
            backstory=(
                "You are a detail-oriented Business Analyst with the ability to interpret "
                "complex business needs from multiple modalities. Your strength lies in "
                "translating unstructured stakeholder information into structured "
                "Business Requirements Documents (BRDs) or Agile User Stories, ensuring "
                "both clarity and feasibility."
            ),
            verbose=True,
            memory=True,
            multimodal=True,
            allow_delegation=True,
            llm=self.llm,
        )

    def invoke(self, stakeholder_inputs: Union[str, List[str]]) -> str:
        """
        Accepts raw project context (str) OR a list of multimodal inputs (file paths, transcripts).
        """
        logger.info(f"[BusinessAnalystAgent] Starting multimodal requirements analysis...")

        current_date = datetime.now().strftime("%Y-%m-%d")

        requirements_analysis_task = Task(
            description=(
                "Conduct requirement gathering and analysis from the provided inputs. "
                "You may receive unstructured text, PDF documents, Word files, images, or audio transcripts. "
                "Extract business needs, functional and non-functional requirements, "
                "and identify gaps, risks, and dependencies.\n\n"
                f"Inputs: {stakeholder_inputs}\n\n"
                "Your role is to translate these into clear, actionable, and traceable requirements."
            ),
            expected_output=(
                "Deliver a structured **Business Requirements Document (BRD)** or **User Stories**. "
                "The output must clearly define:\n"
                "- Business objectives\n"
                "- Functional and non-functional requirements\n"
                "- Acceptance criteria\n"
                "- Dependencies and gaps\n\n"
                f"### Document Metadata\n- Prepared By: Business Analyst Agent\n- Date: {current_date}"
            ),
            agent=self.business_analyst,
            output_file="output/business_requirements.md"
        )

        crew = Crew(
            agents=[self.business_analyst],
            tasks=[requirements_analysis_task],
            process=Process.sequential,
            verbose=True,
        )

        try:
            result = crew.kickoff(inputs={"stakeholder_inputs": stakeholder_inputs})
            logger.info(f"[BusinessAnalystAgent] Crew final response: {result}")
            return str(result)
        except Exception as e:
            logger.error(f"[BusinessAnalystAgent] Crew execution failed: {e}")
            return "Sorry, I couldn't generate the Business Requirements Document at this moment. Please try again later."
