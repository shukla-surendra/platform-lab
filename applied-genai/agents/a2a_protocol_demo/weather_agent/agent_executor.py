"""The weather agent: a minimal A2A "worker" -- deliberately no LLM at all.

This project has two agents; the interesting part is how they *talk to each other*
over the A2A protocol, not what either one does internally. Keeping this one dumb
(a static lookup table) means the coordinator's delegation logic is the only thing
actually doing anything LLM-shaped, so the A2A call itself stays easy to see.
"""

from __future__ import annotations

from a2a.helpers import get_message_text, new_task_from_user_message, new_text_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState

WEATHER = {
    "paris": "18C, light rain",
    "london": "14C, overcast",
    "tokyo": "22C, clear skies",
    "new york": "20C, partly cloudy",
    "san francisco": "16C, foggy",
}


def lookup_weather(query: str) -> str:
    q = query.lower()
    for city, report in WEATHER.items():
        if city in q:
            return f"Weather in {city.title()}: {report}"
    known = ", ".join(city.title() for city in WEATHER)
    return f"I don't have weather data for that city. Known cities: {known}"


class WeatherAgentExecutor(AgentExecutor):
    """A real A2A `AgentExecutor` -- the same interface any agent behind this
    protocol implements, regardless of what's inside `execute` (an LLM, a lookup
    table, a call to yet another agent -- the protocol doesn't care)."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if task is None:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        await updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message("Looking up weather..."),
        )

        query = get_message_text(context.message) or ""
        result = lookup_weather(query)

        await updater.add_artifact(parts=[new_text_part(text=result, media_type="text/plain")])
        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message("Done."),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel is not supported.")
