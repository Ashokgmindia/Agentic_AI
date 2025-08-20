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


class AgileProjectManagerAgent:
    """Agent that facilitates Agile projects and sprint planning."""

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

        # Define Agile Project Manager agent
        self.agile_pm = Agent(
            role="Agile Project Manager",
            goal=(
                "Facilitate agile projects by guiding teams, removing impediments, "
                "and ensuring iterative delivery that aligns with business goals."
            ),
            backstory=(
                "You are an experienced Agile Project Manager who thrives on enabling "
                "teams to deliver value continuously. You excel at fostering collaboration, "
                "tracking progress through agile metrics, and adapting to changing priorities. "
                "Your servant-leadership style empowers teams to self-organize while "
                "keeping stakeholders informed and engaged."
            ),
            verbose=True,
            memory=True,
            allow_delegation=True,
            llm=self.llm,
        )

    def invoke(self, backlog_context: Union[str, List[str]]) -> str:
        """
        Generate a sprint plan based on backlog items, priorities, and business objectives.
        """
        logger.info("[AgileProjectManagerAgent] Starting sprint planning...")

        current_date = datetime.now().strftime("%Y-%m-%d")

        sprint_planning_task = Task(
            description=(
                "Organize and lead a sprint planning session. Gather backlog items, "
                "collaborate with the team to estimate effort, prioritize based on business value, "
                "and create a sprint plan that is realistic and achievable.\n\n"
                "Your final answer MUST include:\n"
                "- A prioritized sprint backlog (5–10 items)\n"
                "- Story point estimates or relative sizing for each item\n"
                "- Clear sprint goals linked to business objectives\n"
                "- Identified potential risks or blockers\n\n"
                f"Inputs: {backlog_context}"
            ),
            expected_output=(
                "A well-structured sprint plan with backlog items, estimates, goals, "
                "and risks documented in a clear format for team and stakeholders.\n\n"
                f"### Document Metadata\n- Prepared By: Agile Project Manager Agent\n- Date: {current_date}"
            ),
            agent=self.agile_pm,
            output_file="output/sprint_plan.md",
        )

        crew = Crew(
            agents=[self.agile_pm],
            tasks=[sprint_planning_task],
            process=Process.sequential,
            verbose=True,
        )

        try:
            result = crew.kickoff(inputs={"backlog_context": backlog_context})
            logger.info(f"[AgileProjectManagerAgent] Crew final response: {result}")
            return str(result)
        except Exception as e:
            logger.error(f"[AgileProjectManagerAgent] Crew execution failed: {e}")
            return (
                "Sorry, I couldn't generate the Sprint Plan at this moment. "
                "Please try again later."
            )


# if __name__ == "__main__":
#     # Example usage
#     agent = AgileProjectManagerAgent()
#     output = agent.invoke("Backlog: User login, Dashboard analytics, Payment gateway integration, Notifications, Admin panel")
#     print(output)
