# ruff: noqa
# Copyright 2026 Google LLC
# Wanderlust AI Root Agent

import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import (
    AgentEngineSandboxCodeExecutor,
)
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from .a2ui_utils import a2ui_callback
from .tools import (
    add_destination,
    calculate_trip_budget,
    find_nearby_places,
    generate_destination_artwork,
    generate_destination_video,
    geocode_address,
    get_destination_details,
    get_live_destination_weather,
    search_destinations,
)


# Parse Agent Engine resource from deployment_metadata.json
_metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
_agent_engine_resource = None
if _metadata_path.exists():
    try:
        with open(_metadata_path) as _f:
            _metadata = json.load(_f)
            _agent_engine_resource = _metadata.get("remote_agent_runtime_id")
    except Exception:
        pass

if not _agent_engine_resource:
    _agent_engine_resource = (
        "projects/969012190709/locations/us-east1/reasoningEngines/3304461251001712640"
    )

MEMORY_BANK_ID = _agent_engine_resource.split("/")[-1]


def memory_bank_service_builder():
    """Returns a VertexAiMemoryBankService instance for Agent Engine deployment."""
    return VertexAiMemoryBankService(
        project="qwiklabs-gcp-02-a4ec6fc6c34a",
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )


memory_service = memory_bank_service_builder()


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, send the session to Memory Bank for extraction."""
    await callback_context.add_session_to_memory()
    return None


def get_weather(query: str) -> str:
    """Simulates a web search for weather information.

    Args:
        query: Location string.

    Returns:
        Simulated weather report string.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting current local time for a city.

    Args:
        query: City name string.

    Returns:
        Formatted local time string.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are Wanderlust AI, an expert personal travel concierge. "
        "Help travelers discover destinations, generate travel artwork/postcards, geocode locations, search nearby attractions, check live weather, calculate trip budgets, execute Python code in a secure sandbox, and manage destinations. "
        "You remember the user's stated travel preferences, food/dietary/medical/environmental allergies, budget constraints, and favorite destinations across sessions to personalize your recommendations. "
        "Always pay close attention to any user allergies and ensure all travel itineraries, dining recommendations, and activity suggestions explicitly respect and accommodate them."
    ),
    workflow_description=(
        "Use your travel tools (`generate_destination_artwork`, `geocode_address`, `find_nearby_places`, `search_destinations`, `get_destination_details`, `get_live_destination_weather`, `calculate_trip_budget`, `add_destination`) "
        "and your code execution sandbox whenever users ask for calculations, data analysis, code execution, travel recommendations, or trip planning. "
        "Analyze the request and return structured UI when appropriate."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=_agent_engine_resource,
    ),
    tools=[
        PreloadMemoryTool(),
        generate_destination_artwork,
        generate_destination_video,
        geocode_address,
        find_nearby_places,
        search_destinations,
        get_destination_details,
        get_live_destination_weather,
        calculate_trip_budget,
        add_destination,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
