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
from agile_project_manager import AgileProjectManagerAgent

logger = logging.getLogger(__name__)


# ---------------- Stakeholder ----------------
class StakeholderAgentExecutor(AgentExecutor):
    """AgentExecutor for the Stakeholder Requirements Analysis agent."""

    def __init__(self):
        try:
            self.agent = StakeholderAgent()
        except Exception as e:
            logger.error(f"Failed to initialize StakeholderAgent: {e}")
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

        try:
            result = self.agent.invoke(context.get_user_input())
            logger.info(f"StakeholderAgent result: {result}")
        except Exception as e:
            logger.error(f"Error invoking StakeholderAgent: {e}")
            raise ServerError(error=InternalError()) from e

        parts = [Part(root=TextPart(text=result))]
        await updater.add_artifact(parts)
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.warning("Cancel operation not supported.")
        raise ServerError(error=UnsupportedOperationError())

    def _validate_request(self, context: RequestContext) -> bool:
        try:
            user_input = context.get_user_input()
            return not user_input or not user_input.strip()
        except Exception:
            return True


# ---------------- Business Analyst ----------------
class BusinessAnalystAgentExecutor(AgentExecutor):
    """AgentExecutor for the Business Analyst agent."""

    def __init__(self):
        try:
            self.agent = BusinessAnalystAgent()
        except Exception as e:
            logger.error(f"Failed to initialize BusinessAnalystAgent: {e}")
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

        try:
            result = self.agent.invoke(context.get_user_input())
            logger.info(f"BusinessAnalystAgent result: {result}")
        except Exception as e:
            logger.error(f"Error invoking BusinessAnalystAgent: {e}")
            raise ServerError(error=InternalError()) from e

        parts = [Part(root=TextPart(text=result))]
        await updater.add_artifact(parts)
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.warning("Cancel operation not supported.")
        raise ServerError(error=UnsupportedOperationError())

    def _validate_request(self, context: RequestContext) -> bool:
        try:
            user_input = context.get_user_input()
            return not user_input or not user_input.strip()
        except Exception:
            return True


# ---------------- Domain Expert ----------------
class DomainExpertAgentExecutor(AgentExecutor):
    """AgentExecutor for the Business Analyst Domain Expert agent."""

    def __init__(self):
        try:
            self.agent = BusinessAnalystDomainExpert()
        except Exception as e:
            logger.error(f"Failed to initialize BusinessAnalystDomainExpert: {e}")
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

        try:
            result = self.agent.invoke(context.get_user_input())
            logger.info(f"DomainExpertAgent result: {result}")
        except Exception as e:
            logger.error(f"Error invoking DomainExpertAgent: {e}")
            raise ServerError(error=InternalError()) from e

        parts = [Part(root=TextPart(text=result))]
        await updater.add_artifact(parts)
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.warning("Cancel operation not supported.")
        raise ServerError(error=UnsupportedOperationError())

    def _validate_request(self, context: RequestContext) -> bool:
        try:
            user_input = context.get_user_input()
            return not user_input or not user_input.strip()
        except Exception:
            return True


# ---------------- Product Manager ----------------
class ProductManagerAgentExecutor(AgentExecutor):
    """AgentExecutor for the Product Manager agent."""

    def __init__(self):
        try:
            self.agent = ProductManagerAgent()
        except Exception as e:
            logger.error(f"Failed to initialize ProductManagerAgent: {e}")
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

        try:
            result = self.agent.invoke(context.get_user_input())
            logger.info(f"ProductManagerAgent result: {result}")
        except Exception as e:
            logger.error(f"Error invoking ProductManagerAgent: {e}")
            raise ServerError(error=InternalError()) from e

        parts = [Part(root=TextPart(text=result))]
        await updater.add_artifact(parts)
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.warning("Cancel operation not supported.")
        raise ServerError(error=UnsupportedOperationError())

    def _validate_request(self, context: RequestContext) -> bool:
        try:
            user_input = context.get_user_input()
            return not user_input or not user_input.strip()
        except Exception:
            return True


# ---------------- Agile Project Manager ----------------
class AgileProjectManagerAgentExecutor(AgentExecutor):
    """AgentExecutor for the Agile Project Manager agent."""

    def __init__(self):
        try:
            self.agent = AgileProjectManagerAgent()
        except Exception as e:
            logger.error(f"Failed to initialize AgileProjectManagerAgent: {e}")
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

        try:
            result = self.agent.invoke(context.get_user_input())
            logger.info(f"AgileProjectManagerAgent result: {result}")
        except Exception as e:
            logger.error(f"Error invoking AgileProjectManagerAgent: {e}")
            raise ServerError(error=InternalError()) from e

        parts = [Part(root=TextPart(text=result))]
        await updater.add_artifact(parts)
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.warning("Cancel operation not supported.")
        raise ServerError(error=UnsupportedOperationError())

    def _validate_request(self, context: RequestContext) -> bool:
        try:
            user_input = context.get_user_input()
            return not user_input or not user_input.strip()
        except Exception:
            return True
