"""Math A2A Agent implementation.

Contains the math evaluation logic, Agent Card definition,
and the MathAgentExecutor adhering to A2A protocol specifications.
"""

import ast
import logging
import math
import operator
import re
from typing import Any

from a2a.helpers import get_message_text, new_text_message
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Role,
)

logger = logging.getLogger("math_a2a_agent")

# Safe math operators for AST evaluation
SAFE_OPERATORS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Safe mathematical functions and constants
SAFE_FUNCTIONS: dict[str, Any] = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "pow": pow,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pi": math.pi,
    "e": math.e,
}


def _eval_ast_node(node: ast.AST) -> float | int:
    """Safely evaluates an AST node containing mathematical expressions."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    if isinstance(node, ast.BinOp):
        left = _eval_ast_node(node.left)
        right = _eval_ast_node(node.right)
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")

    if isinstance(node, ast.UnaryOp):
        operand = _eval_ast_node(node.operand)
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
            func = SAFE_FUNCTIONS[node.func.id]
            args = [_eval_ast_node(arg) for arg in node.args]
            return func(*args)
        func_name = getattr(node.func, "id", "<unknown>")
        raise ValueError(f"Function '{func_name}' is not allowed in calculations.")

    if isinstance(node, ast.Name):
        if node.id in SAFE_FUNCTIONS:
            val = SAFE_FUNCTIONS[node.id]
            if isinstance(val, (int, float)):
                return val
        raise ValueError(f"Variable or identifier '{node.id}' is not recognized.")

    raise ValueError(f"Syntax element '{type(node).__name__}' is not supported.")


def evaluate_math_expression(raw_input: str) -> str:
    """Extracts and evaluates mathematical expressions safely.

    Examples:
        - "Calculate 25 * 4" -> "100"
        - "What is 12 + 15?" -> "27"
        - "Compute 100 / 5"  -> "20"
        - "sqrt(16) + 10"    -> "14"
    """
    if not raw_input or not raw_input.strip():
        raise ValueError("Empty request. Please provide a mathematical expression to calculate.")

    cleaned = raw_input.strip()

    # Strip conversational prefixes
    cleaned = re.sub(
        r"^(?:calculate|compute|solve|what\s+is|evaluate|can\s+you\s+calculate|please\s+calculate)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # Strip trailing punctuation marks commonly found in queries
    cleaned = cleaned.rstrip("?.! \t\n")

    # Replace caret ^ with exponentiation **
    cleaned = cleaned.replace("^", "**")

    if not cleaned:
        raise ValueError("No mathematical expression found in request.")

    try:
        parsed = ast.parse(cleaned, mode="eval")
        result = _eval_ast_node(parsed.body)
    except SyntaxError as e:
        raise ValueError(f"Invalid mathematical expression syntax: {cleaned}") from e
    except ZeroDivisionError as e:
        raise ValueError("Division by zero is undefined.") from e

    # Format result: If integer or float with no fractional part, return integer string
    if isinstance(result, float) and result.is_integer():
        return str(int(result))

    return str(result)


def create_agent_card(agent_url: str = "http://localhost:8000") -> AgentCard:
    """Builds the A2A v1.0 Agent Card descriptor for the Math Agent."""
    skill = AgentSkill(
        id="calculate",
        name="Calculate",
        description="Performs basic mathematical calculations.",
        tags=["math", "calculator", "arithmetic"],
        examples=[
            "Calculate 25 * 4",
            "What is 12 + 15?",
            "Compute 100 / 5",
            "Evaluate 2 ** 8",
        ],
        input_modes=["text/plain", "application/json"],
        output_modes=["text/plain", "application/json"],
    )

    card = AgentCard(
        name="Math A2A Agent",
        description="A clean A2A Agent that performs mathematical calculations.",
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url=agent_url.rstrip("/"),
                protocol_version="1.0",
                protocol_binding="JSONRPC",
            )
        ],
        skills=[skill],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
        ),
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["text/plain", "application/json"],
    )

    return card


class MathAgentExecutor(AgentExecutor):
    """Executes incoming A2A tasks by processing mathematical calculations."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handles incoming A2A execution requests."""
        logger.info(
            "A2A request received: context_id=%s, task_id=%s",
            context.context_id,
            context.task_id,
        )

        user_input = get_message_text(context.message) if context.message else ""
        logger.info("Processing message: '%s'", user_input)

        try:
            logger.info("Performing mathematical calculation...")
            result_text = evaluate_math_expression(user_input)
            logger.info("Calculation successful: '%s' = '%s'", user_input, result_text)
        except Exception as exc:
            logger.warning("Calculation failed for '%s': %s", user_input, str(exc))
            result_text = f"Error: {exc}"

        response_message = new_text_message(
            text=result_text,
            context_id=context.context_id,
            task_id=context.task_id,
            role=Role.ROLE_AGENT,
        )

        logger.info(
            "Returning A2A response: context_id=%s, task_id=%s, text='%s'",
            context.context_id,
            context.task_id,
            result_text,
        )
        await event_queue.enqueue_event(response_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handles A2A task cancellation."""
        logger.info(
            "Task cancellation requested: context_id=%s, task_id=%s",
            context.context_id,
            context.task_id,
        )
