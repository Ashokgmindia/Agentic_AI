import logging
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import InternalError, InvalidParamsError, Part, TextPart, UnsupportedOperationError
from a2a.utils.errors import ServerError

from Stakeholder_Agent import StakeholderAgent
from BusinessAnalyst_Agent import BusinessAnalystAgent
from business_analyst_domain_expert import BusinessAnalystDomainExpert
from product_manager import ProductManagerAgent
from agile_project_manager import AgileProjectManagerAgent  # NEW

logger = logging.getLogger(__name__)


class UnifiedAgentExecutor(AgentExecutor):
    """
    A single AgentExecutor that can run different agents 
    (StakeholderAgent, BusinessAnalystAgent, BusinessAnalystDomainExpert,
     ProductManagerAgent, AgileProjectManagerAgent).

    Strategy:
    - Picks an agent based on `context.agent_type` OR user input keywords.
    - Runs the agent's `invoke()` method.
    - Streams the result back via TaskUpdater.
    """

    def __init__(self):
        try:
            self.agents = {
                "stakeholder": StakeholderAgent(),
                "business_analyst": BusinessAnalystAgent(),
                "domain_expert": BusinessAnalystDomainExpert(),
                "product_manager": ProductManagerAgent(),
                "agile_pm": AgileProjectManagerAgent(),  # LAST
            }
        except Exception as e:
            logger.error(f"Failed to initialize one of the agents: {e}")
            raise

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if not context.task_id or not context.context_id:
            raise ValueError("RequestContext must have task_id and context_id")
        if not context.message:
            raise ValueError("RequestContext must have a message")

        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        if not context.current_task:
            await updater.submit()
        await updater.start_work()

        if self._validate_request(context):
            raise ServerError(error=InvalidParamsError())

        # Decide which agent to run
        agent_key = self._select_agent(context)
        agent = self.agents.get(agent_key)
        if not agent:
            logger.error(f"No agent found for key: {agent_key}")
            raise ServerError(error=InvalidParamsError())

        stakeholder_inputs = context.get_user_input()
        try:
            result = agent.invoke(stakeholder_inputs)
            logger.info(f"{agent_key} result: {result}")
        except Exception as e:
            logger.error(f"Error invoking {agent_key}: {e}")
            raise ServerError(error=InternalError()) from e

        parts = [Part(root=TextPart(text=result))]
        await updater.add_artifact(parts)
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.warning("Cancel operation not supported for UnifiedAgentExecutor.")
        raise ServerError(error=UnsupportedOperationError())

    def _validate_request(self, context: RequestContext) -> bool:
        try:
            user_input = context.get_user_input()
            return not user_input or not str(user_input).strip()
        except Exception:
            return True

    def _select_agent(self, context: RequestContext) -> str:
        """
        Determine which agent to use.
        Priority:
        1. Explicit context.agent_type
        2. Keywords in user input
        3. Default fallback → business_analyst
        """
        if hasattr(context, "agent_type") and context.agent_type:
            return context.agent_type.lower()

        try:
            user_input = context.get_user_input()
            msg = user_input.lower()
        except Exception:
            msg = ""

        if "stakeholder" in msg:
            return "stakeholder"
        if "domain expert" in msg or "expert" in msg:
            return "domain_expert"
        if "business" in msg or "analyst" in msg:
            return "business_analyst"
        if "product manager" in msg or "roadmap" in msg:
            return "product_manager"
        if "agile" in msg or "sprint" in msg or "scrum" in msg:  # NEW
            return "agile_pm"

        # Default fallback
        return "business_analyst"
