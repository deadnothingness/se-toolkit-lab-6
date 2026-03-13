"""Simple regression test for agent.py."""

import json
import subprocess
import sys


def test_agent_basic_call():
    """Test that agent.py returns valid JSON with answer and tool_calls."""
    result = subprocess.run(
        [sys.executable, "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    
    data = json.loads(result.stdout.strip())
    assert "answer" in data
    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)
    assert data["answer"]

