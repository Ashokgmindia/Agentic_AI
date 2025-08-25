import asyncio
import json
import uuid
import base64
from datetime import datetime
from typing import Any, AsyncIterable, List, Callable
import mimetypes

import httpx
import nest_asyncio
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types
import logging

load_dotenv()
nest_asyncio.apply()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# RemoteAgentConnections
# -------------------------------------------------------------------
TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """Holds the connections to remote agents."""

    def __init__(self, agent_card: AgentCard, agent_url: str):
        logger.info(f"Initializing connection - Agent: {agent_card.name}, URL: {agent_url}")
        # Increase timeout for file uploads
        self._httpx_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))  # 2 minutes
        self.agent_client = A2AClient(self._httpx_client, agent_card, url=agent_url)
        self.card = agent_card
        self.conversation_name = None
        self.conversation = None
        self.pending_tasks = set()

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(
        self, message_request: SendMessageRequest
    ) -> SendMessageResponse:
        """Send a message to the remote agent (task is created automatically)."""
        try:
            logger.info(f"Sending message to {self.card.name}")
            response = await self.agent_client.send_message(message_request)
            logger.info(f"Received response from {self.card.name}")
            return response
        except Exception as e:
            logger.error(f"Error sending message to {self.card.name}: {e}")
            raise


# -------------------------------------------------------------------
# HostAgent
# -------------------------------------------------------------------
class HostAgent:
    """The Host agent for multi-agent orchestration (supports multimodal)."""

    def __init__(self):
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""
        self._agent = self.create_agent()
        self._user_id = "host_agent"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def _async_init_components(self, remote_agent_addresses: List[str]):
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            for address in remote_agent_addresses:
                card_resolver = A2ACardResolver(client, address)
                try:
                    logger.info(f"Getting agent card from {address}")
                    card = await card_resolver.get_agent_card()
                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                    self.remote_agent_connections[card.name] = remote_connection
                    self.cards[card.name] = card
                    logger.info(f"Successfully connected to agent: {card.name}")
                except httpx.ConnectError as e:
                    logger.error(f"Connection error for {address}: {e}")
                except Exception as e:
                    logger.error(f"Failed to initialize connection for {address}: {e}")

        agent_info = [
            json.dumps({"name": card.name, "description": card.description})
            for card in self.cards.values()
        ]
        logger.info(f"Available agents: {[card.name for card in self.cards.values()]}")
        self.agents = "\n".join(agent_info) if agent_info else "No agents found"

    @classmethod
    async def create(cls, remote_agent_addresses: List[str]):
        instance = cls()
        await instance._async_init_components(remote_agent_addresses)
        return instance

    def create_agent(self) -> Agent:
        return Agent(
            model="gemini-2.5-flash",
            name="Host_Agent",
            instruction=self.root_instruction,
            description="This Host agent orchestrates tasks and scheduling with remote agents.",
            tools=[self.send_message],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        return f"""
        **Role:** You are the Host Agent, an expert orchestrator for task coordination and scheduling.

        **Directives:**
        * Analyze tasks and delegate to the right remote agents.
        * Use `send_message` to communicate with agents.
        * You may send multimodal inputs: text, images, PDFs, Word docs, or structured data.
        * Integrate responses into clear outputs (including multimodal artifacts).
        * Always show which agents you contacted and why.
        * Only rely on available tools & agent responses.
        * For file uploads, ensure proper format conversion and error handling.

        **Today's Date:** {datetime.now().strftime("%Y-%m-%d")}

        <Available Agents>
        {self.agents}
        </Available Agents>
        """

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(role="user", parts=[types.Part.from_text(text=query)])
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        
        try:
            async for event in self._runner.run_async(
                user_id=self._user_id, session_id=session.id, new_message=content
            ):
                if event.is_final_response():
                    response_parts = []
                    if event.content and event.content.parts:
                        for p in event.content.parts:
                            if p.text:
                                response_parts.append({"type": "text", "text": p.text})
                            elif p.inline_data:
                                response_parts.append({"type": "file", "file": p.inline_data})
                    yield {
                        "is_task_complete": True,
                        "content": response_parts,
                    }
                else:
                    yield {
                        "is_task_complete": False,
                        "updates": "The host agent is thinking...",
                    }
        except Exception as e:
            logger.error(f"Error in stream processing: {e}")
            yield {
                "is_task_complete": True,
                "content": [{"type": "text", "text": f"Error processing request: {str(e)}"}],
            }

    async def send_message(self, agent_name: str, parts: list[dict], tool_context: ToolContext):
        """Sends a multimodal task to a remote agent."""
        logger.info(f"send_message called with agent_name: {agent_name}")
        logger.info(f"Parts received: {len(parts)} parts")
        
        if agent_name not in self.remote_agent_connections:
            error_msg = f"Agent {agent_name} not found. Available agents: {list(self.remote_agent_connections.keys())}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        client = self.remote_agent_connections[agent_name]

        # ---------------- Enhanced Normalization ----------------
        normalized_parts = []
        for i, part in enumerate(parts):
            logger.info(f"Processing part {i}: {type(part)}")
            
            if not isinstance(part, dict):
                normalized_parts.append({"type": "text", "text": str(part)})
                continue

            ptype = part.get("type")
            logger.info(f"Part type: {ptype}, Part keys: {list(part.keys())}")

            if ptype == "text":
                normalized_parts.append({"type": "text", "text": part.get("text", "")})

            elif ptype == "file":
                if "file" not in part:
                    logger.error(f"Malformed file part: {part}")
                    raise ValueError(f"Malformed file part: {part}")
                
                file_data = part["file"]
                logger.info(f"File data keys: {list(file_data.keys()) if isinstance(file_data, dict) else 'Not a dict'}")
                
                # Handle different file data formats
                if isinstance(file_data, dict):
                    # Ensure required fields
                    if "name" not in file_data:
                        file_data["name"] = f"file_{uuid.uuid4().hex}"
                    if "mimeType" not in file_data and "mime_type" in file_data:
                        file_data["mimeType"] = file_data["mime_type"]
                    elif "mimeType" not in file_data:
                        # Try to guess mime type from name
                        file_name = file_data.get("name", "")
                        mime_type, _ = mimetypes.guess_type(file_name)
                        file_data["mimeType"] = mime_type or "application/octet-stream"
                
                normalized_parts.append({"type": "file", "file": file_data})

            elif ptype == "data":
                if "data" not in part:
                    logger.error(f"Malformed data part: {part}")
                    raise ValueError(f"Malformed data part: {part}")
                normalized_parts.append({"type": "data", "data": part["data"]})

            # Handle ADK's {mime_type, file_url} format
            elif "mime_type" in part and "file_url" in part:
                logger.info(f"Converting ADK format: mime_type={part['mime_type']}, file_url={part['file_url']}")
                normalized_parts.append({
                    "type": "file",
                    "file": {
                        "name": part.get("name", f"file_{uuid.uuid4().hex}"),
                        "mimeType": part["mime_type"],
                        "uri": part["file_url"],
                    },
                })

            # Handle inline_data from Google ADK
            elif "inline_data" in part:
                inline_data = part["inline_data"]
                logger.info(f"Processing inline_data: {list(inline_data.keys()) if isinstance(inline_data, dict) else 'Not a dict'}")
                
                if isinstance(inline_data, dict):
                    file_info = {
                        "name": part.get("name", f"file_{uuid.uuid4().hex}"),
                        "mimeType": inline_data.get("mime_type") or inline_data.get("mimeType", "application/octet-stream"),
                    }
                    
                    # Handle different data formats
                    if "data" in inline_data:
                        file_info["bytes"] = inline_data["data"]
                    elif "uri" in inline_data:
                        file_info["uri"] = inline_data["uri"]
                    
                    normalized_parts.append({"type": "file", "file": file_info})

            else:
                # Fallback: try to extract text
                if "text" in part:
                    normalized_parts.append({"type": "text", "text": part["text"]})
                else:
                    logger.warning(f"Unknown part format, converting to text: {part}")
                    normalized_parts.append({"type": "text", "text": str(part)})

        logger.info(f"Normalized {len(normalized_parts)} parts for transmission")
        for i, part in enumerate(normalized_parts):
            if part.get("type") == "file":
                file_info = part.get("file", {})
                logger.info(f"Part {i}: file with mimeType={file_info.get('mimeType')}, name={file_info.get('name')}")
            else:
                logger.info(f"Part {i}: {part.get('type')}")

        # ------------------------------------------------
        context_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        payload = {
            "message": {
                "role": "user",
                "parts": normalized_parts,
                "messageId": message_id,
                "contextId": context_id,
            },
        }

        message_request = SendMessageRequest(
            id=message_id, params=MessageSendParams.model_validate(payload)
        )
        
        logger.info(f"Sending request to {agent_name} with {len(normalized_parts)} parts")
        
        try:
            send_response: SendMessageResponse = await client.send_message(message_request)
            logger.info(f"Received response from {agent_name}")
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout error when sending to {agent_name}: {e}")
            return [{"type": "text", "text": f"Timeout error communicating with {agent_name}. The request may have been too large or the agent is busy."}]
        except Exception as e:
            logger.error(f"Error sending message to {agent_name}: {e}")
            return [{"type": "text", "text": f"Error communicating with {agent_name}: {str(e)}"}]

        if not isinstance(send_response.root, SendMessageSuccessResponse) or not isinstance(send_response.root.result, Task):
            logger.error("Received a non-success or non-task response")
            return [{"type": "text", "text": "Received invalid response from remote agent"}]

        response_content = send_response.root.model_dump_json(exclude_none=True)
        json_content = json.loads(response_content)

        resp = []
        if json_content.get("result", {}).get("artifacts"):
            for artifact in json_content["result"]["artifacts"]:
                if artifact.get("parts"):
                    resp.extend(artifact["parts"])
        elif json_content.get("result", {}).get("text"):
            resp.append({"type": "text", "text": json_content["result"]["text"]})
        
        logger.info(f"Returning {len(resp)} response parts from {agent_name}")
        return resp


# -------------------------------------------------------------------
# Helper: build multimodal parts
# -------------------------------------------------------------------
def build_parts(text: str = None, file_path: str = None, file_uri: str = None, mime_type: str = None) -> list[dict]:
    parts = []
    if text:
        parts.append({"type": "text", "text": text})
    if file_path:
        try:
            with open(file_path, "rb") as f:
                content = base64.b64encode(f.read()).decode()
            
            # Auto-detect mime type if not provided
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(file_path)
                mime_type = mime_type or "application/octet-stream"
            
            parts.append({
                "type": "file",
                "file": {
                    "name": file_path.split("/")[-1], 
                    "mimeType": mime_type, 
                    "bytes": content
                }
            })
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            parts.append({"type": "text", "text": f"Error reading file: {str(e)}"})
    
    if file_uri:
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_uri)
            mime_type = mime_type or "application/octet-stream"
        
        parts.append({
            "type": "file",
            "file": {
                "name": file_uri.split("/")[-1], 
                "mimeType": mime_type, 
                "uri": file_uri
            }
        })
    return parts


# -------------------------------------------------------------------
# Sync init
# -------------------------------------------------------------------
def _get_initialized_host_agent_sync():
    async def _async_main():
        remote_agent_urls = ["http://localhost:10004","http://localhost:10005",
                             "http://localhost:10006", "http://localhost:10007", "http://localhost:10008","http://localhost:10009"]
        logger.info("Initializing host agent...")
        hosting_agent_instance = await HostAgent.create(
            remote_agent_addresses=remote_agent_urls
        )
        logger.info("HostAgent initialized successfully")
        return hosting_agent_instance.create_agent()

    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            logger.warning(
                f"Could not initialize HostAgent with asyncio.run(): {e}. "
                "This can happen if an event loop is already running (e.g., in Jupyter). "
                "Consider initializing HostAgent within an async function in your application."
            )
        else:
            raise


root_agent = _get_initialized_host_agent_sync()