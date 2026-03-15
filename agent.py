#!/usr/bin/env python3
"""Documentation agent with file reading tools and agentic loop.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "source": "...", "tool_calls": [...]}
    All debug output goes to stderr.

Tools:
    - list_files: List files and directories at a given path
    - read_file: Read contents of a file
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


# ============================================================================
# Configuration and constants
# ============================================================================

MAX_TOOL_CALLS = 10
PROJECT_ROOT = Path(__file__).parent.absolute()


# ============================================================================
# Environment loading
# ============================================================================

def load_env(env_path: str) -> dict[str, str]:
    """Load environment variables from a .env file."""
    env_vars = {}
    path = Path(env_path)
    if not path.exists():
        raise FileNotFoundError(f"Environment file not found: {env_path}")

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env_vars[key] = value
    return env_vars


# ============================================================================
# Security: prevent path traversal attacks
# ============================================================================

def is_path_safe(requested_path: str) -> tuple[bool, Path]:
    """Check if path is within project root and return resolved absolute path.

    Args:
        requested_path: Path relative to project root

    Returns:
        Tuple of (is_safe, resolved_absolute_path)
    """
    try:
        # Resolve the full path, preventing directory traversal
        full_path = (PROJECT_ROOT / requested_path).resolve()
        # Check if it's within project root
        if PROJECT_ROOT not in full_path.parents and full_path != PROJECT_ROOT:
            return False, full_path
        return True, full_path
    except Exception:
        return False, Path()


# ============================================================================
# Tool implementations
# ============================================================================

def list_files(path: str = ".") -> str:
    """List files and directories at the given path.

    Args:
        path: Directory path relative to project root

    Returns:
        Newline-separated list of entries, or error message
    """
    safe, full_path = is_path_safe(path)

    if not safe:
        return f"ERROR: Access denied - path '{path}' is outside project directory"

    if not full_path.exists():
        return f"ERROR: Path '{path}' does not exist"

    if not full_path.is_dir():
        return f"ERROR: '{path}' is not a directory"

    try:
        entries = sorted(full_path.iterdir())
        names = [e.name + ("/" if e.is_dir() else "") for e in entries]
        return "\n".join(names)
    except Exception as e:
        return f"ERROR: {str(e)}"


def read_file(path: str) -> str:
    """Read contents of a file.

    Args:
        path: File path relative to project root

    Returns:
        File contents as string, or error message
    """
    safe, full_path = is_path_safe(path)

    if not safe:
        return f"ERROR: Access denied - path '{path}' is outside project directory"

    if not full_path.exists():
        return f"ERROR: File '{path}' does not exist"

    if not full_path.is_file():
        return f"ERROR: '{path}' is not a file"

    try:
        return full_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: {str(e)}"


# ============================================================================
# Tool schemas for LLM function calling
# ============================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this to discover what documentation is available in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to project root (e.g., 'wiki' or '.')",
                        "default": "."
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use this to examine documentation files and find answers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to project root (e.g., 'wiki/git-workflow.md')",
                    }
                },
                "required": ["path"],
            },
        },
    },
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "list_files": list_files,
    "read_file": read_file,
}


# ============================================================================
# LLM API calls
# ============================================================================

def call_llm_with_tools(
    messages: List[Dict[str, str]],
    api_key: str,
    api_base: str,
    model: str,
    tools: Optional[List[Dict]] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Call LLM with optional tools.

    Args:
        messages: Conversation history
        api_key: API key for authentication
        api_base: Base URL of the API
        model: Model name to use
        tools: Optional list of tool schemas
        timeout: Request timeout in seconds

    Returns:
        Parsed JSON response from the API

    Raises:
        httpx.HTTPStatusError: On HTTP error
        httpx.RequestError: On network error
        httpx.TimeoutException: On timeout
    """
    url = f"{api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
    }

    if tools:
        payload["tools"] = tools
        # Optional: force tool usage with tool_choice
        # payload["tool_choice"] = "auto"

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


# ============================================================================
# Agentic loop
# ============================================================================

def agentic_loop(
    question: str,
    api_key: str,
    api_base: str,
    model: str,
) -> Dict[str, Any]:
    """Run the agentic loop to answer a question using tools.

    Args:
        question: User's question
        api_key: API key for authentication
        api_base: Base URL of the API
        model: Model name to use

    Returns:
        Dictionary with answer, source, and tool_calls
    """
    print(f"🤖 Processing: {question}", file=sys.stderr)

    # Initialize messages with system prompt
    messages = [
        {
            "role": "system",
            "content": (
                "You are a documentation assistant for the Software Engineering Toolkit project. "
                "Your goal is to answer questions about the project using the available documentation files.\n\n"
                "Available tools:\n"
                "- `list_files`: List files and directories to discover what documentation is available\n"
                "- `read_file`: Read the contents of a file to find answers\n\n"
                "Instructions:\n"
                "1. Use `list_files` first to explore the 'wiki' directory and see what documentation exists\n"
                "2. Use `read_file` to examine relevant files and find the answer\n"
                "3. When you find the answer, include the source reference in the format: `wiki/filename.md#section`\n"
                "4. Format your final answer exactly as:\n"
                "   ANSWER: <your answer>\n"
                "   SOURCE: <source reference>\n\n"
                f"You can make up to {MAX_TOOL_CALLS} tool calls. Be efficient - try to find the answer with minimal calls."
            ),
        },
        {"role": "user", "content": question},
    ]

    all_tool_calls = []
    loop_count = 0

    while loop_count < MAX_TOOL_CALLS:
        loop_count += 1
        print(f"\n🔄 Loop {loop_count}/{MAX_TOOL_CALLS}", file=sys.stderr)

        # Call LLM with tools
        try:
            response_data = call_llm_with_tools(
                messages, api_key, api_base, model, TOOLS
            )
        except Exception as e:
            print(f"❌ LLM call failed: {e}", file=sys.stderr)
            # Continue with whatever we have? Better to raise
            raise

        message = response_data["choices"][0]["message"]
        tool_calls = message.get("tool_calls", [])

        # If no tool calls, this should be the final answer
        if not tool_calls:
            content = message.get("content", "")
            print(f"✅ Final response received", file=sys.stderr)

            # Parse answer and source from expected format
            if "ANSWER:" in content and "SOURCE:" in content:
                try:
                    parts = content.split("ANSWER:")[1].strip()
                    answer_parts = parts.split("SOURCE:")
                    answer = answer_parts[0].strip()
                    source = answer_parts[1].strip() if len(answer_parts) > 1 else ""
                except Exception as e:
                    print(f"⚠️ Failed to parse response format: {e}", file=sys.stderr)
                    answer = content
                    source = ""
            else:
                # Fallback if format is wrong
                print(f"⚠️ Response missing expected format (ANSWER:/SOURCE:)", file=sys.stderr)
                answer = content
                source = ""

            return {
                "answer": answer,
                "source": source,
                "tool_calls": all_tool_calls,
            }

        # Record tool calls
        print(f"  🤔 LLM requested {len(tool_calls)} tool(s)", file=sys.stderr)
        messages.append(message)

        # Execute tools
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            tool_id = tool_call["id"]

            print(f"  🔧 Executing: {tool_name}({tool_args})", file=sys.stderr)

            # Execute the tool
            if tool_name in TOOL_FUNCTIONS:
                result = TOOL_FUNCTIONS[tool_name](**tool_args)
            else:
                result = f"ERROR: Unknown tool '{tool_name}'"

            # Add tool result to messages
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result,
                }
            )

            # Record for output
            all_tool_calls.append(
                {
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result,
                }
            )

    # Max loops reached without final answer
    print(f"⚠️ Maximum tool calls ({MAX_TOOL_CALLS}) reached without final answer", file=sys.stderr)
    return {
        "answer": "I couldn't find a complete answer within the tool call limit.",
        "source": "",
        "tool_calls": all_tool_calls,
    }


# ============================================================================
# Main entry point
# ============================================================================

def main() -> int:
    """Main entry point."""
    # Parse command-line arguments
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        return 1

    question = sys.argv[1]

    # Load environment variables
    env_path = Path(__file__).parent / ".env.agent.secret"
    try:
        env = load_env(str(env_path))
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error loading environment: {e}", file=sys.stderr)
        return 1

    # Get required environment variables
    api_key = env.get("LLM_API_KEY")
    api_base = env.get("LLM_API_BASE")
    model = env.get("LLM_MODEL")

    if not api_key:
        print("Error: LLM_API_KEY not found in .env.agent.secret", file=sys.stderr)
        return 1
    if not api_base:
        print("Error: LLM_API_BASE not found in .env.agent.secret", file=sys.stderr)
        return 1
    if not model:
        print("Error: LLM_MODEL not found in .env.agent.secret", file=sys.stderr)
        return 1

    print(f"Using model: {model}", file=sys.stderr)
    print(f"API base: {api_base}", file=sys.stderr)

    # Run the agentic loop
    try:
        result = agentic_loop(question, api_key, api_base, model)
    except httpx.TimeoutException:
        print("Error: Request timed out (60s)", file=sys.stderr)
        return 1
    except httpx.HTTPStatusError as e:
        print(f"Error: HTTP error {e.response.status_code}: {e.response.text[:200]}", file=sys.stderr)
        return 1
    except httpx.RequestError as e:
        print(f"Error: Request failed: {e}", file=sys.stderr)
        return 1
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"Error: Failed to parse LLM response: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

    # Output result as JSON
    print(json.dumps(result, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
    