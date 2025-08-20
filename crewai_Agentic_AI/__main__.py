import logging
import os
import uvicorn
import asyncio
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from Stakeholder_Agent import StakeholderAgent
from BusinessAnalyst_Agent import BusinessAnalystAgent
from business_analyst_domain_expert import BusinessAnalystDomainExpert
from product_manager import ProductManagerAgent
from agile_project_manager import AgileProjectManagerAgent

# ✅ Import the 5 executors
from agent_executor import (
    StakeholderAgentExecutor,
    BusinessAnalystAgentExecutor,
    DomainExpertAgentExecutor,
    ProductManagerAgentExecutor,
    AgileProjectManagerAgentExecutor,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


def create_stakeholder_app(host: str, port: int):
    capabilities = AgentCapabilities(streaming=False)
    skill = AgentSkill(
        id="stakeholder_requirements_analyst",
        name="Stakeholder Requirements Analyst",
        description="Analyzes multimodal stakeholder inputs and generates comprehensive BRDs with governance compliance.",
        tags=[
            "vision-document-analysis",
            "stakeholder-input",
            "project-scope-discovery",
            "requirement-elicitation",
            "strategy-to-insight",
            "early-phase-analysis"
        ],
        examples=[
            "Analyze this project vision document and summarize the main objectives and scope boundaries",
            "Extract key stakeholder expectations from a strategy presentation PDF",
            "Process meeting notes from a client kickoff session to identify functional goals",
            "Review a stakeholder-submitted project charter and highlight ambiguous requirements",
            "Interpret annotated mockups from a product owner to uncover implied functionality",
        ],
    )
    agent_card = AgentCard(
        name="Stakeholder Requirements Agent",
        description="Processes multimodal stakeholder inputs (text, docs, images, audio) into audit-ready project vision document.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=StakeholderAgent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=["text/markdown"],
        capabilities=capabilities,
        skills=[skill],
    )
    handler = DefaultRequestHandler(agent_executor=StakeholderAgentExecutor(), task_store=InMemoryTaskStore())
    return A2AStarletteApplication(agent_card=agent_card, http_handler=handler)


def create_business_app(host: str, port: int):
    capabilities = AgentCapabilities(streaming=False)
    skill = AgentSkill(
        id="business_analyst_general",
        name="Business Analyst (General)",
        description="Gathers and analyzes project requirements from multimodal inputs, producing BRDs or User Stories.",
        tags=["business-analysis", "requirements", "user-stories", "BRD"],
        examples=[
            "Gather requirements for a new CRM system from interview transcripts",
            "Analyze these feature requests and turn them into User Stories",
            "Generate a BRD for an internal HR management platform",
        ],
    )
    agent_card = AgentCard(
        name="Business Analyst Agent",
        description="Translates business needs into actionable BRDs and User Stories with clear objectives and acceptance criteria.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=BusinessAnalystAgent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=["text/markdown"],
        capabilities=capabilities,
        skills=[skill],
    )
    handler = DefaultRequestHandler(agent_executor=BusinessAnalystAgentExecutor(), task_store=InMemoryTaskStore())
    return A2AStarletteApplication(agent_card=agent_card, http_handler=handler)


def create_domain_expert_app(host: str, port: int):
    capabilities = AgentCapabilities(streaming=False)
    skill = AgentSkill(
        id="business_analyst_domain_expert",
        name="Business Analyst (Domain Expert)",
        description="Provides deep domain expertise, aligning requirements with industry standards, regulations, and best practices.",
        tags=["business-analysis", "requirements", "BRD", "domain-expert", "compliance"],
        examples=[
            "Review healthcare compliance requirements and produce a BRD",
            "Analyze banking regulations and align them with project objectives",
            "Generate User Stories for an insurance system ensuring domain compliance",
        ],
    )
    agent_card = AgentCard(
        name="Business Analyst Domain Expert Agent",
        description="Ingests multimodal stakeholder inputs and produces traceable BRDs/User Stories aligned with domain standards.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=BusinessAnalystDomainExpert.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=["text/markdown"],
        capabilities=capabilities,
        skills=[skill],
    )
    handler = DefaultRequestHandler(agent_executor=DomainExpertAgentExecutor(), task_store=InMemoryTaskStore())
    return A2AStarletteApplication(agent_card=agent_card, http_handler=handler)


def create_product_manager_app(host: str, port: int):
    capabilities = AgentCapabilities(streaming=False)
    skill = AgentSkill(
        id="product_manager",
        name="Product Manager",
        description="Defines product vision, strategy, and roadmap to maximize business value and customer satisfaction.",
        tags=["product-management", "roadmap", "strategy", "customer-feedback"],
        examples=[
            "Create a 6-month roadmap for a new e-commerce platform",
            "Analyze market trends and define product milestones",
            "Turn customer feedback into prioritized roadmap items",
        ],
    )
    agent_card = AgentCard(
        name="Product Manager Agent",
        description="Creates actionable product roadmaps with priorities, timelines, and success metrics.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=ProductManagerAgent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=["text/markdown"],
        capabilities=capabilities,
        skills=[skill],
    )
    handler = DefaultRequestHandler(agent_executor=ProductManagerAgentExecutor(), task_store=InMemoryTaskStore())
    return A2AStarletteApplication(agent_card=agent_card, http_handler=handler)


def create_agile_pm_app(host: str, port: int):
    capabilities = AgentCapabilities(streaming=False)
    skill = AgentSkill(
        id="agile_pm",
        name="Agile Project Manager",
        description="Facilitates agile projects by guiding teams, organizing sprint planning, and ensuring delivery aligns with business goals.",
        tags=["agile", "scrum", "sprint-planning", "project-management"],
        examples=[
            "Plan the next sprint with backlog items and estimates",
            "Create a sprint plan for a mobile app release",
            "Identify blockers for an agile team working on a new feature",
        ],
    )
    agent_card = AgentCard(
        name="Agile Project Manager Agent",
        description="Generates sprint plans with backlog items, estimates, goals, and risks for agile teams.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=AgileProjectManagerAgent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=["text/markdown"],
        capabilities=capabilities,
        skills=[skill],
    )
    handler = DefaultRequestHandler(agent_executor=AgileProjectManagerAgentExecutor(), task_store=InMemoryTaskStore())
    return A2AStarletteApplication(agent_card=agent_card, http_handler=handler)


async def main():
    host = "localhost"
    try:
        if not os.getenv("GEMINI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            raise MissingAPIKeyError("Either GEMINI_API_KEY or OPENAI_API_KEY must be set in .env.")

        # Build apps
        stakeholder_app = create_stakeholder_app(host, 10004)
        business_app = create_business_app(host, 10005)
        domain_expert_app = create_domain_expert_app(host, 10006)
        product_manager_app = create_product_manager_app(host, 10007)
        agile_pm_app = create_agile_pm_app(host, 10008)

        # Configs
        config1 = uvicorn.Config(stakeholder_app.build(), host=host, port=10004, log_level="info")
        config2 = uvicorn.Config(business_app.build(), host=host, port=10005, log_level="info")
        config3 = uvicorn.Config(domain_expert_app.build(), host=host, port=10006, log_level="info")
        config4 = uvicorn.Config(product_manager_app.build(), host=host, port=10007, log_level="info")
        config5 = uvicorn.Config(agile_pm_app.build(), host=host, port=10008, log_level="info")

        # Servers
        server1 = uvicorn.Server(config1)
        server2 = uvicorn.Server(config2)
        server3 = uvicorn.Server(config3)
        server4 = uvicorn.Server(config4)
        server5 = uvicorn.Server(config5)

        logger.info(
            "Starting Stakeholder (10004), Business Analyst (10005), Domain Expert (10006), "
            "Product Manager (10007), and Agile Project Manager (10008)..."
        )
        await asyncio.gather(
            server1.serve(),
            server2.serve(),
            server3.serve(),
            server4.serve(),
            server5.serve(),
        )

    except MissingAPIKeyError as e:
        logger.error(f"Configuration error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
