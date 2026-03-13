"""Regression tests for agent.py CLI."""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_returns_valid_json():
    """Test that agent.py outputs valid JSON with required fields.

    This test runs agent.py as a subprocess with a simple question,
    parses the stdout as JSON, and verifies that:
    - The output is valid JSON
    - The 'answer' field exists and is non-empty
    - The 'tool_calls' field exists and is an array
    """
    # Path to agent.py (project root is 2 levels up from backend/tests/unit)
    project_root = Path(__file__).parent.parent.parent.parent
    agent_path = project_root / "agent.py"

    # Run agent.py with a simple question
    result = subprocess.run(
        [sys.executable, str(agent_path), "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"

    # Check stdout is not empty
    assert result.stdout.strip(), "Agent produced no output"

    # Parse JSON
    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout[:200]}") from e

    # Check required fields
    assert "answer" in data, "Missing 'answer' field in output"
    assert data["answer"], "'answer' field is empty"
    assert isinstance(data["answer"], str), "'answer' field is not a string"

    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' field is not an array"
