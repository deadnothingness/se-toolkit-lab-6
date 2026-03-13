#!/usr/bin/env python3
"""CLI agent that answers questions using an LLM.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "tool_calls": []}
    All debug output goes to stderr.
"""

import json
import os
import sys
from pathlib import Path

import httpx


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


def call_llm(question: str, api_key: str, api_base: str, model: str, timeout: int = 60) -> str:
    """Call the LLM API and return the answer.

    Args:
        question: The user's question
        api_key: API key for authentication
        api_base: Base URL of the API (e.g., http://localhost:42005/v1)
        model: Model name to use
        timeout: Request timeout in seconds

    Returns:
        The answer text from the LLM

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
        "messages": [{"role": "user", "content": question}],
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    # Extract answer from OpenAI-compatible response format
    answer = data["choices"][0]["message"]["content"]
    return answer


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

    print(f"Calling LLM with model '{model}'...", file=sys.stderr)

    # Call the LLM
    try:
        answer = call_llm(question, api_key, api_base, model)
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

    print(f"Got answer from LLM", file=sys.stderr)

    # Output result as JSON
    result = {
        "answer": answer,
        "tool_calls": [],
    }
    print(json.dumps(result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
