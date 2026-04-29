"""Tool calling loop — permite al LLM llamar herramientas y usar los resultados.

Integra las herramientas del tool_layer con el LLM router para que los
agentes puedan ejecutar acciones reales (leer/escribir archivos, correr
comandos, buscar en web, git, github, etc.) de forma autónoma.

El LLM recibe tool definitions y puede responder con tool calls.
El loop ejecuta las tools, inyecta los resultados, y repite hasta
que el LLM termina o se alcanza el máximo de iteraciones.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from synto.tools.tool_layer import TOOL_REGISTRY, execute_tool


@dataclass
class ToolCall:
    """Una llamada a herramienta generada por el LLM."""
    name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass
class ToolResult:
    """Resultado de ejecutar una herramienta."""
    call_id: str
    tool_name: str
    output: Any
    is_error: bool = False


@dataclass
class ToolCallingConfig:
    """Configuración del tool calling para un agente."""
    enabled: bool = True
    max_iterations: int = 20
    allowed_tools: list[str] = field(default_factory=list)  # empty = all
    denied_tools: list[str] = field(default_factory=list)
    # Tool output size limits
    max_output_chars: int = 30000


def get_tool_definitions(allowed: list[str] | None = None, denied: list[str] | None = None) -> list[dict[str, Any]]:
    """Generar tool definitions en formato OpenAI function calling."""
    definitions = []
    for name, meta in TOOL_REGISTRY.items():
        if denied and name in denied:
            continue
        if allowed and name not in allowed:
            continue

        # Build JSON Schema for parameters
        properties = {}
        required = []
        for param_name, param_info in meta["parameters"].items():
            prop = {"type": param_info.get("type", "string")}
            if "description" in param_info:
                prop["description"] = param_info["description"]
            if "enum" in param_info:
                prop["enum"] = param_info["enum"]
            if "default" in param_info:
                prop["default"] = param_info["default"]
            else:
                required.append(param_name)
            if param_info.get("items"):
                prop["items"] = param_info["items"]
            properties[param_name] = prop

        definitions.append({
            "type": "function",
            "function": {
                "name": name,
                "description": meta["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        })
    return definitions


def parse_tool_calls_from_response(content: str) -> list[ToolCall]:
    """Parsear tool calls del contenido del LLM.

    Soporta dos formatos:
    1. JSON block: ```json\n{"tool_calls": [...]}\n```
    2. XML-style: <tool_call name="x" args='{"y": 1}' />
    3. Function calling format de OpenAI (si el provider lo soporta)
    """
    tool_calls = []

    # Format 1: JSON block
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "tool_calls" in data:
                items = data["tool_calls"]
            elif isinstance(data, dict) and "name" in data:
                items = [data]
            else:
                items = []

            for item in items:
                if isinstance(item, dict) and "name" in item:
                    tool_calls.append(ToolCall(
                        name=item["name"],
                        arguments=item.get("arguments", item.get("args", {})),
                        call_id=item.get("call_id", item.get("id", "")),
                    ))
            if tool_calls:
                return tool_calls
        except (json.JSONDecodeError, KeyError):
            pass

    # Format 2: XML-style tags
    for match in re.finditer(r'<tool_call\s+name="([^"]+)"\s+args=\'([^\']+)\'\s*/?>', content):
        try:
            args = json.loads(match.group(2))
            tool_calls.append(ToolCall(name=match.group(1), arguments=args, call_id=match.group(0)[:16]))
        except json.JSONDecodeError:
            pass

    # Format 3: OpenAI function calling in metadata
    for match in re.finditer(r'<function_call>(.*?)</function_call>', content, re.DOTALL):
        try:
            fc = json.loads(match.group(1))
            tool_calls.append(ToolCall(
                name=fc.get("name", ""),
                arguments=fc.get("arguments", {}) if isinstance(fc.get("arguments"), dict) else json.loads(fc.get("arguments", "{}")),
                call_id=fc.get("call_id", ""),
            ))
        except (json.JSONDecodeError, KeyError):
            pass

    return tool_calls


def execute_tool_call(call: ToolCall, config: ToolCallingConfig | None = None) -> ToolResult:
    """Ejecutar una llamada a herramienta y devolver el resultado."""
    if config and config.denied_tools and call.name in config.denied_tools:
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.name,
            output={"error": f"Tool '{call.name}' is denied for this agent"},
            is_error=True,
        )
    if config and config.allowed_tools and call.name not in config.allowed_tools:
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.name,
            output={"error": f"Tool '{call.name}' is not in the allowed list"},
            is_error=True,
        )

    try:
        result = execute_tool(call.name, **call.arguments)
        # Truncate large outputs
        result_str = json.dumps(result, default=str) if not isinstance(result, str) else result
        if config and len(result_str) > config.max_output_chars:
            result_str = result_str[:config.max_output_chars] + f"\n... (truncated, {len(result_str)} total chars)"
            result = result_str
        is_error = isinstance(result, dict) and "error" in result and len(result) <= 3
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.name,
            output=result,
            is_error=is_error,
        )
    except Exception as e:
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.name,
            output={"error": str(e)},
            is_error=True,
        )


def build_tool_results_prompt(results: list[ToolResult]) -> str:
    """Construir un prompt con los resultados de las herramientas."""
    if not results:
        return ""

    parts = ["--- Tool Execution Results ---\n"]
    for r in results:
        status = "ERROR" if r.is_error else "OK"
        output = r.output if isinstance(r.output, str) else json.dumps(r.output, default=str, indent=2)
        parts.append(f"[{status}] {r.tool_name}:\n{output}\n")
    parts.append("--- Use these results to continue with your task. ---\n")
    return "\n".join(parts)


def build_tool_instructions_prompt(definitions: list[dict[str, Any]]) -> str:
    """Construir instrucciones sobre cómo usar las herramientas."""
    if not definitions:
        return ""

    tool_names = [d["function"]["name"] for d in definitions]
    categories = {}
    for d in definitions:
        cat = d["function"].get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(d["function"]["name"])

    parts = [
        "--- Available Tools ---",
        "",
        f"You have access to {len(tool_names)} tools that you can use to complete your task.",
        "",
        "To use a tool, respond with a JSON block:",
        "",
        "```json",
        '{"tool_calls": [{"name": "tool_name", "arguments": {"arg1": "value1"}}]}',
        "```",
        "",
        "You can call multiple tools in a single response.",
        "After receiving tool results, continue working on the task.",
        "",
        "Available tools by category:",
    ]
    for cat, names in sorted(categories.items()):
        parts.append(f"  {cat}: {', '.join(names)}")

    parts.append("")
    parts.append("--- End Available Tools ---\n")
    return "\n".join(parts)


@dataclass
class ToolCallingResult:
    """Resultado del tool calling loop."""
    final_content: str
    tool_calls_made: int = 0
    iterations: int = 0
    tool_results: list[ToolResult] = field(default_factory=list)
    all_tool_output: str = ""


def tool_calling_loop(
    llm_generate,  # callable(prompt) -> (content, metadata)
    initial_prompt: str,
    tool_definitions: list[dict[str, Any]],
    config: ToolCallingConfig | None = None,
) -> ToolCallingResult:
    """Loop principal de tool calling.

    1. Envía el prompt al LLM con tool definitions
    2. Si el LLM llama tools, las ejecuta
    3. Inyecta los resultados y repite
    4. Termina cuando el LLM no llama más tools o se alcanza max_iterations
    """
    if config is None:
        config = ToolCallingConfig()

    if not config.enabled or not tool_definitions:
        # Sin tool calling — solo generar
        content, meta = llm_generate(initial_prompt)
        return ToolCallingResult(
            final_content=content,
            tool_calls_made=0,
            iterations=1,
        )

    tool_instructions = build_tool_instructions_prompt(tool_definitions)
    full_prompt = f"{tool_instructions}\n{initial_prompt}"

    all_tool_output = ""
    total_calls = 0
    iteration = 0
    all_results = []

    while iteration < config.max_iterations:
        iteration += 1

        # Generar respuesta del LLM
        content, meta = llm_generate(full_prompt)

        # Parsear tool calls
        calls = parse_tool_calls_from_response(content)

        if not calls:
            # No hay tool calls — el LLM terminó
            return ToolCallingResult(
                final_content=content,
                tool_calls_made=total_calls,
                iterations=iteration,
                tool_results=all_results,
                all_tool_output=all_tool_output,
            )

        # Ejecutar tools
        results = []
        for call in calls:
            result = execute_tool_call(call, config)
            results.append(result)
            total_calls += 1

        all_results.extend(results)

        # Construir prompt con resultados
        results_prompt = build_tool_results_prompt(results)
        for r in results:
            output = r.output if isinstance(r.output, str) else json.dumps(r.output, default=str)
            all_tool_output += f"[{r.tool_name}] {output[:500]}\n"

        # Preparar siguiente iteración
        full_prompt = f"{content}\n\n{results_prompt}"

    # Max iterations reached
    return ToolCallingResult(
        final_content=content + f"\n\n[Tool calling stopped: max {config.max_iterations} iterations reached]",
        tool_calls_made=total_calls,
        iterations=iteration,
        tool_results=all_results,
        all_tool_output=all_tool_output,
    )
