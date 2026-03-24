"""LLM API client for AI-powered intent routing with tool calling."""

import json
import logging
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Tool definitions for all 9 backend endpoints
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "Get list of all labs and tasks. Use this to discover what labs are available.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "Get list of enrolled students and their groups. Use for queries about students, enrollment, or groups.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": "Get score distribution (4 buckets) for a specific lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-01', 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task average scores and attempt counts for a lab. Use for queries about task difficulty or pass rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-01', 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": "Get submissions per day for a lab. Use for queries about submission patterns or activity over time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-01', 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get per-group performance and student counts for a lab. Use for comparing groups.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-01', 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": "Get top N learners by score for a lab. Use for leaderboards or finding best students.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-01', 'lab-04'"},
                    "limit": {"type": "integer", "description": "Number of top learners to return, default 5"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": "Get completion rate percentage for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-01', 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": "Trigger ETL sync to refresh data from autochecker. Use when user asks to refresh or update data.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

# System prompt for the LLM
SYSTEM_PROMPT = """You are an AI assistant for a Learning Management System (LMS). Your job is to help users understand lab assignments, scores, and student performance.

You have access to tools that fetch data from the backend API. When a user asks a question:
1. First, think about what data you need to answer the question
2. Call the appropriate tools to get that data
3. Once you have the data, analyze it and provide a clear, helpful answer

For multi-step queries (like "which lab has the lowest pass rate?"), you should:
1. First call get_items to get all labs
2. Then call get_pass_rates for each lab
3. Compare the results and identify the lowest
4. Report your findings with specific numbers

Always be specific and include numbers when available. Format your responses clearly.

If the user's message is a greeting or casual conversation, respond naturally without using tools.

If you don't understand the user's message, ask for clarification or explain what you can help with.

Available tools:
- get_items: List all labs and tasks
- get_learners: List enrolled students and groups
- get_scores: Score distribution for a lab
- get_pass_rates: Per-task pass rates for a lab
- get_timeline: Submissions per day for a lab
- get_groups: Per-group performance for a lab
- get_top_learners: Top N learners for a lab
- get_completion_rate: Completion rate for a lab
- trigger_sync: Refresh data from autochecker
"""


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    name: str
    arguments: Dict[str, Any]
    call_id: str


class LLMClient:
    """Client for interacting with the LLM API with tool calling support."""

    def __init__(self, api_key: str, base_url: str, model: str = "qwen-coder"):
        """Initialize the LLM client.

        Args:
            api_key: API key for authentication.
            base_url: Base URL of the LLM API.
            model: Model name to use.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _debug(self, message: str) -> None:
        """Print debug message to stderr."""
        print(f"[tool] {message}", file=sys.stderr)

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_iterations: int = 5,
    ) -> str:
        """Send a chat message with tool calling support.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions.
            max_iterations: Maximum number of tool call iterations.

        Returns:
            The LLM's final response text.
        """
        if tools is None:
            tools = TOOL_DEFINITIONS

        conversation = list(messages)  # Copy to avoid modifying input

        for iteration in range(max_iterations):
            self._debug(f"Iteration {iteration + 1}: Calling LLM")

            response = await self._call_llm(conversation, tools)

            # Check if LLM returned a tool call
            if response.get("choices") and len(response["choices"]) > 0:
                choice = response["choices"][0]
                message = choice.get("message", {})

                # Check for tool calls
                tool_calls = message.get("tool_calls", [])
                if tool_calls:
                    # Execute tool calls and collect results
                    tool_results = []
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        name = func.get("name", "")
                        args_str = func.get("arguments", "{}")
                        call_id = tc.get("id", f"call_{iteration}")

                        try:
                            args = json.loads(args_str) if isinstance(args_str, str) else args_str
                        except json.JSONDecodeError:
                            args = {}

                        self._debug(f"LLM called: {name}({args})")

                        # Execute the tool
                        result = await self._execute_tool(name, args)
                        self._debug(f"Result: {result[:100] if len(result) > 100 else result}")

                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": result,
                        })

                    self._debug(f"Feeding {len(tool_results)} tool result(s) back to LLM")

                    # Add assistant message with tool calls
                    conversation.append({
                        "role": "assistant",
                        "content": message.get("content"),
                        "tool_calls": tool_calls,
                    })

                    # Add tool results
                    conversation.extend(tool_results)

                    continue  # Continue loop to get final answer
                else:
                    # No tool calls, return the content
                    content = message.get("content", "")
                    self._debug(f"[summary] Final response: {content[:50]}...")
                    return content

        # Max iterations reached, return last content
        return "I'm having trouble processing your request. Please try rephrasing."

    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Make a direct API call to the LLM.

        Args:
            messages: Conversation messages.
            tools: Optional tool definitions.

        Returns:
            Raw API response dict.
        """
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,  # Low temperature for consistent tool calling
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"  # Let LLM decide when to use tools

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self._headers,
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()

    async def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return the result as a string.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool result as a formatted string.
        """
        from .lms_client import LMSClient

        # Import config - handle both module and direct execution
        try:
            from ..config import load_config
        except ImportError:
            from config import load_config

        try:
            config = load_config(require_bot_token=False)
            lms = LMSClient(config.lms_api_base_url, config.lms_api_key)

            if name == "get_items":
                items = await lms.get_items()
                # Format items for LLM
                lines = []
                for item in items:
                    item_type = item.get("type", "unknown")
                    item_id = item.get("id", "")
                    title = item.get("title", item.get("name", "Unknown"))
                    if isinstance(item_id, int):
                        item_id = f"lab-{item_id:02d}"
                    lines.append(f"- [{item_type}] {item_id}: {title}")
                return f"Found {len(items)} items:\n" + "\n".join(lines)

            elif name == "get_learners":
                learners = await lms.get_learners()
                lines = []
                for learner in learners[:20]:  # Limit to first 20
                    name = learner.get("name", "Unknown")
                    group = learner.get("group", "Unknown")
                    lines.append(f"- {name} ({group})")
                if len(learners) > 20:
                    lines.append(f"... and {len(learners) - 20} more")
                return f"Found {len(learners)} learners:\n" + "\n".join(lines)

            elif name == "get_scores":
                lab = arguments.get("lab", "")
                scores = await lms.get_scores(lab)
                lines = []
                for bucket in scores:
                    if isinstance(bucket, dict):
                        range_label = bucket.get("range", "")
                        count = bucket.get("count", 0)
                    else:
                        range_label = getattr(bucket, 'range', '')
                        count = getattr(bucket, 'count', 0)
                    lines.append(f"- {range_label}: {count} students")
                return f"Score distribution for {lab}:\n" + "\n".join(lines)

            elif name == "get_pass_rates":
                lab = arguments.get("lab", "")
                pass_rates = await lms.get_pass_rates(lab)
                lines = []
                for pr in pass_rates:
                    # Handle both dict and TaskPassRate dataclass
                    if isinstance(pr, dict):
                        task = pr.get("task", pr.get("task_name", "Unknown"))
                        avg = pr.get("avg_score", pr.get("average", 0))
                        attempts = pr.get("attempts", pr.get("submissions", 0))
                    else:
                        # TaskPassRate dataclass
                        task = getattr(pr, 'task_name', 'Unknown Task')
                        avg = getattr(pr, 'pass_rate', 0)
                        attempts = getattr(pr, 'attempts', 0)
                    lines.append(f"- {task}: {avg:.1f}% ({attempts} attempts)")
                return f"Pass rates for {lab}:\n" + "\n".join(lines)

            elif name == "get_timeline":
                lab = arguments.get("lab", "")
                timeline = await lms.get_timeline(lab)
                lines = []
                for entry in timeline[:10]:  # Limit to first 10 days
                    if isinstance(entry, dict):
                        date = entry.get("date", "")
                        count = entry.get("count", 0)
                    else:
                        date = getattr(entry, 'date', '')
                        count = getattr(entry, 'count', 0)
                    lines.append(f"- {date}: {count} submissions")
                if len(timeline) > 10:
                    lines.append(f"... and {len(timeline) - 10} more days")
                return f"Timeline for {lab}:\n" + "\n".join(lines)

            elif name == "get_groups":
                lab = arguments.get("lab", "")
                groups = await lms.get_groups(lab)
                lines = []
                for g in sorted(groups, key=lambda x: x.get("avg_score", 0) if isinstance(x, dict) else getattr(x, 'avg_score', 0), reverse=True):
                    if isinstance(g, dict):
                        name = g.get("group", g.get("name", "Unknown"))
                        avg = g.get("avg_score", 0)
                        count = g.get("student_count", g.get("count", 0))
                    else:
                        name = getattr(g, 'group', getattr(g, 'name', 'Unknown'))
                        avg = getattr(g, 'avg_score', 0)
                        count = getattr(g, 'student_count', getattr(g, 'count', 0))
                    lines.append(f"- {name}: {avg:.1f}% avg ({count} students)")
                return f"Group performance for {lab}:\n" + "\n".join(lines)

            elif name == "get_top_learners":
                lab = arguments.get("lab", "")
                limit = arguments.get("limit", 5)
                top = await lms.get_top_learners(lab, limit)
                lines = []
                for i, learner in enumerate(top, 1):
                    if isinstance(learner, dict):
                        name = learner.get("name", "Unknown")
                        score = learner.get("score", learner.get("avg_score", 0))
                        group = learner.get("group", "")
                    else:
                        name = getattr(learner, 'name', 'Unknown')
                        score = getattr(learner, 'score', getattr(learner, 'avg_score', 0))
                        group = getattr(learner, 'group', '')
                    group_str = f" ({group})" if group else ""
                    lines.append(f"{i}. {name}{group_str}: {score:.1f}%")
                return f"Top {len(top)} learners for {lab}:\n" + "\n".join(lines)

            elif name == "get_completion_rate":
                lab = arguments.get("lab", "")
                rate = await lms.get_completion_rate(lab)
                if isinstance(rate, dict):
                    completion = rate.get("completion_rate", rate.get("rate", 0))
                    completed = rate.get("completed", 0)
                    total = rate.get("total", 0)
                else:
                    completion = getattr(rate, 'completion_rate', getattr(rate, 'rate', 0))
                    completed = getattr(rate, 'completed', 0)
                    total = getattr(rate, 'total', 0)
                return f"Completion rate for {lab}: {completion:.1f}% ({completed}/{total} students)"

            elif name == "trigger_sync":
                result = await lms.trigger_sync()
                status = result.get("status", "unknown")
                message = result.get("message", "")
                return f"Sync triggered: {status}. {message}"

            else:
                return f"Unknown tool: {name}"

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.exception(f"Tool {name} failed")
            return f"Error executing {name}: {error_msg}"

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """Send a chat message to the LLM (without tools).

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            The LLM's response text.
        """
        logger.info(f"Sending chat to LLM with {len(messages)} messages")
        response = await self._call_llm(messages, tools=None)

        if response.get("choices") and len(response["choices"]) > 0:
            return response["choices"][0].get("message", {}).get("content", "")
        return "I'm sorry, I couldn't process that request."

    async def classify_intent(self, text: str) -> str:
        """Classify the intent of a user message using keyword matching.

        Args:
            text: The user's message text.

        Returns:
            The classified intent (e.g., 'start', 'help', 'labs', 'scores').
        """
        logger.info(f"Classifying intent for: {text[:50]}...")

        text_lower = text.lower()

        # Check for start/welcome intents
        if any(kw in text_lower for kw in ["start", "hello", "hi ", "hey", "begin", "welcome"]):
            return "start"

        # Check for help intents
        if any(kw in text_lower for kw in ["help", "command", "what can", "how to", "how do", "usage"]):
            return "help"

        # Check for health/status intents
        if any(kw in text_lower for kw in ["health", "status", "online", "working", "system"]):
            return "health"

        # Check for labs intents
        if any(kw in text_lower for kw in ["lab", "assignment", "available"]):
            return "labs"

        # Check for scores intents
        if any(kw in text_lower for kw in ["score", "grade", "result", "mark"]):
            return "scores"

        return "unknown"

    async def health_check(self) -> bool:
        """Check if the LLM API is healthy.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            messages = [{"role": "user", "content": "hi"}]
            response = await self._call_llm(messages, tools=None)
            return response.get("choices") is not None
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False
