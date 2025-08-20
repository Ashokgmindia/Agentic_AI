import os
import logging
from datetime import datetime
from typing import Union, List

from dotenv import load_dotenv
from crewai import LLM, Agent, Crew, Process, Task

# Load environment variables
load_dotenv()

# Logger setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ProductManagerAgent:
    """Agent that defines product vision, strategy, and roadmap."""

    SUPPORTED_CONTENT_TYPES = ["text/plain"]

    def __init__(self):
        # Load LLM (Gemini preferred, fallback to OpenAI)
        if os.getenv("GEMINI_API_KEY"):
            self.llm = LLM(
                model="gemini/gemini-2.5-flash-lite-preview-06-17",
                api_key=os.getenv("GEMINI_API_KEY"),
            )
        elif os.getenv("OPENAI_API_KEY"):
            self.llm = LLM(
                model="gpt-4o-mini",
                api_key=os.getenv("OPENAI_API_KEY"),
            )
        else:
            raise ValueError(
                "Neither GEMINI_API_KEY nor OPENAI_API_KEY environment variable is set."
            )

        # Define Product Manager agent
        self.product_manager = Agent(
            role="Product Manager",
            goal=(
                "Define the product vision, strategy, and roadmap to deliver maximum "
                "business value and customer satisfaction."
            ),
            backstory=(
                "You are a strategic Product Manager who thrives at the intersection "
                "of business, technology, and customer experience. You excel at gathering "
                "market insights, prioritizing features, and collaborating across teams to "
                "ensure products are valuable, viable, and feasible."
            ),
            verbose=True,
            memory=True,
            allow_delegation=True,
            llm=self.llm,
        )

    def invoke(self, stakeholder_inputs: Union[str, List[str]]) -> str:
        """
        Generate a product roadmap based on customer feedback, market trends, and business objectives.
        """
        logger.info("[ProductManagerAgent] Starting roadmap definition...")

        current_date = datetime.now().strftime("%Y-%m-%d")

        define_roadmap_task = Task(
            description=(
                "Analyze customer feedback, market trends, and business objectives to "
                "create a product roadmap. The roadmap should highlight high-priority "
                "features, clear timelines, and measurable success criteria.\n\n"
                "Your final answer MUST include:\n"
                "- A 3-6 month roadmap with major milestones\n"
                "- The reasoning behind prioritization of features\n"
                "- Success metrics for each milestone\n\n"
                f"Inputs: {stakeholder_inputs}"
            ),
            expected_output=(
                "A structured product roadmap (with milestones, priorities, and metrics) "
                "that aligns business goals with customer needs.\n\n"
                f"### Document Metadata\n- Prepared By: Product Manager Agent\n- Date: {current_date}"
            ),
            agent=self.product_manager,
            output_file="output/product_roadmap.md",
        )

        crew = Crew(
            agents=[self.product_manager],
            tasks=[define_roadmap_task],
            process=Process.sequential,
            verbose=True,
        )

        try:
            result = crew.kickoff(inputs={"stakeholder_inputs": stakeholder_inputs})
            logger.info(f"[ProductManagerAgent] Crew final response: {result}")
            return str(result)
        except Exception as e:
            logger.error(f"[ProductManagerAgent] Crew execution failed: {e}")
            return (
                "Sorry, I couldn't generate the Product Roadmap at this moment. "
                "Please try again later."
            )


if __name__ == "__main__":
    # Example usage
    agent = ProductManagerAgent()
    output = agent.invoke("We want to launch a mobile app with AI-driven recommendations.")
    print(output)
