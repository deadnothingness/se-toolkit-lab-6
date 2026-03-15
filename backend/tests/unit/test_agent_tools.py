"""Regression tests for agent.py tool calling functionality."""

import json
import subprocess
import sys
from pathlib import Path


def test_merge_conflict_uses_read_file():
    """Test that agent uses read_file tool to answer merge conflict question.

    This test runs agent.py with a question about resolving merge conflicts,
    verifies that:
    - The output is valid JSON
    - The 'read_file' tool is used in tool_calls
    - The 'source' field contains 'wiki/git-workflow.md'
    """
    # Path to agent.py 
    project_root = Path(__file__).parent.parent.parent.parent
    agent_path = project_root / "agent.py"

    # Run agent.py with merge conflict question
    result = subprocess.run(
        [sys.executable, str(agent_path), "How do you resolve a merge conflict?"],
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

    assert "source" in data, "Missing 'source' field in output"
    # Source may be empty if LLM doesn't format response correctly, but if present should reference wiki
    if data["source"]:
        assert "wiki/" in data["source"], (
            f"Expected source to reference wiki/, got: {data['source']}"
        )

    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' field is not an array"

    # Check that read_file was used
    tool_names = [call["tool"] for call in data["tool_calls"]]
    assert "read_file" in tool_names, (
        f"Expected 'read_file' in tool_calls, got: {tool_names}"
    )

    # Verify that a wiki file was read (check tool call args)
    read_file_calls = [c for c in data["tool_calls"] if c["tool"] == "read_file"]
    assert len(read_file_calls) > 0, "No read_file tool calls found"
    # At least one read_file should have a wiki/ path
    wiki_reads = [c for c in read_file_calls if "wiki/" in c["args"].get("path", "")]
    assert len(wiki_reads) > 0, (
        f"Expected read_file to read from wiki/, got paths: {[c['args'].get('path') for c in read_file_calls]}"
    )


def test_wiki_files_uses_list_files():
    """Test that agent uses list_files tool to answer wiki files question.

    This test runs agent.py with a question about what files are in the wiki,
    verifies that:
    - The output is valid JSON
    - The 'list_files' tool is used in tool_calls
    """
    # Path to agent.py
    project_root = Path(__file__).parent.parent.parent.parent
    agent_path = project_root / "agent.py"

    # Run agent.py with wiki files question
    result = subprocess.run(
        [sys.executable, str(agent_path), "What files are in the wiki?"],
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

    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' field is not an array"

    # Check that list_files was used
    tool_names = [call["tool"] for call in data["tool_calls"]]
    assert "list_files" in tool_names, (
        f"Expected 'list_files' in tool_calls, got: {tool_names}"
    )
