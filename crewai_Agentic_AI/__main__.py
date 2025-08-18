import logging
import os
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from Stakeholder_Agent import StakeholderAgent
from agent_executor import StakeholderAgentExecutor
from dotenv import load_dotenv


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MissingAPIKeyError(Exception):
    """Exception for missing API key."""

def main():
    host = "localhost"
    port = 10004
    try:
        
        if not os.getenv("GEMINI_API_KEY"):
            raise MissingAPIKeyError("GEMINI_API_KEY must be set in .env.")

       
        capabilities = AgentCapabilities(streaming=False)
        skill = AgentSkill(
            id="stakeholder_requirements_analyst",
            name="Stakeholder Requirements Analyst",
            description="Intelligently analyzes stakeholder inputs and generates comprehensive Business Requirements Documents (BRDs) with governance compliance and traceability.",
            tags=["business-analysis", "requirements", "BRD", "stakeholder-management", "governance", "compliance"],
            examples=[
                "Analyze these meeting notes and create a BRD for our new customer portal project",
                "Generate requirements document from this product vision document",
                "Create a BRD based on stakeholder interviews about the mobile app redesign",
                "Process these user stories and compliance requirements into a formal BRD",
            ],
        )

        
        agent_host_url = os.getenv("HOST_OVERRIDE") or f"http://{host}:{port}/"
        agent_card = AgentCard(
            name="Stakeholder Requirements Agent",
            description="An intelligent agent that processes multimodal stakeholder inputs (text, documents, images, audio) and synthesizes them into comprehensive, audit-ready Business Requirements Documents with full traceability and compliance considerations.",
            url=agent_host_url,
            version="1.0.0",
            defaultInputModes=StakeholderAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=["text/markdown"],
            capabilities=capabilities,
            skills=[skill],
        )

        # Server setup
        request_handler = DefaultRequestHandler(
            agent_executor=StakeholderAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )
        server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

        logger.info(f"Stakeholder Requirements Agent running at {agent_host_url}")
        uvicorn.run(server.build(), host=host, port=port)

    except MissingAPIKeyError as e:
        logger.error(f"Configuration error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)

if __name__ == "__main__":
    main()