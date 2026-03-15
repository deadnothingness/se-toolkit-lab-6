# Agent Architecture

## Overview

This project implements a CLI agent (`agent.py`) that answers questions by calling an LLM API with tool-calling capabilities. The agent can read documentation files from the project wiki using two tools (`list_files`, `read_file`) and follows an agentic loop to iteratively explore and find answers with source references.

## LLM Provider

- **Provider:** Qwen Code API (self-hosted via `qwen-code-oai-proxy`)
- **Model:** `qwen3-coder-plus`
- **API Compatibility:** OpenAI-compatible chat completions API
- **Daily Limit:** 1000 free requests per day

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  CLI Input      │────▶│  agent.py    │────▶│  LLM API        │────▶│  Tool Call?  │
│  (question)     │     │  (agentic    │     │  (qwen3-coder)  │     └──────────────┘
└─────────────────┘     │   loop)      │                │              │
                        │              │◀───────────────┘              │
                        │              │                               │
                        │              │◀──────────────────────────────┘
                        │              │      Execute tool, append result
                        │              │
                        ▼
                 ┌─────────────────┐
                 │  JSON Output    │
                 │  (answer +      │
                 │   source +      │
                 │   tool_calls)   │
                 └─────────────────┘
```

### Data Flow (Agentic Loop)

1. **Input Parsing:** The agent reads the question from `sys.argv[1]`
2. **Environment Loading:** Reads `.env.agent.secret` for API credentials
3. **Initial LLM Call:** Sends system prompt + user question + tool schemas
4. **Tool Call Check:**
   - **If `tool_calls` present:** Execute each tool, append results as `tool` role messages, repeat from step 3
   - **If no tool calls:** Extract answer and source from final response
5. **Output:** Prints JSON with `answer`, `source`, and `tool_calls` to stdout

### Loop Termination

- **Normal:** LLM returns a text response without tool calls (final answer)
- **Max iterations:** Stops after 10 tool calls to prevent infinite loops

## Tools

The agent has two tools registered as function-calling schemas:

### `list_files`

Lists files and directories at a given path relative to the project root.

```json
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
      "required": ["path"]
    }
  }
}
```

**Implementation:**
- Validates path is within project root using `is_path_safe()`
- Returns newline-separated list of entries (directories end with `/`)
- Returns error message if path doesn't exist or is outside project

### `read_file`

Reads the contents of a file at a given path relative to the project root.

```json
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
          "description": "File path relative to project root (e.g., 'wiki/git-workflow.md')"
        }
      },
      "required": ["path"]
    }
  }
}
```

**Implementation:**
- Validates path is within project root using `is_path_safe()`
- Returns file contents as UTF-8 string
- Returns error message if file doesn't exist or is a directory

### Security: Path Traversal Prevention

Both tools use `is_path_safe()` to prevent accessing files outside the project:

```python
def is_path_safe(requested_path: str) -> tuple[bool, Path]:
    """Check if path is within project root and return resolved absolute path."""
    full_path = (PROJECT_ROOT / requested_path).resolve()
    # Check if it's within project root
    if PROJECT_ROOT not in full_path.parents and full_path != PROJECT_ROOT:
        return False, full_path
    return True, full_path
```

This prevents attacks like `read_file("../../etc/passwd")`.

## System Prompt Strategy

The system prompt guides the LLM to:

1. **Discover first:** Use `list_files` to explore the `wiki` directory structure
2. **Read relevant files:** Use `read_file` to examine specific documentation files
3. **Cite sources:** Include source references in format `wiki/filename.md#section`
4. **Be efficient:** Find answers with minimal tool calls (max 10)

```python
SYSTEM_PROMPT = """
You are a documentation assistant for the Software Engineering Toolkit project.
Your goal is to answer questions about the project using the available documentation files.

Available tools:
- `list_files`: List files and directories to discover what documentation is available
- `read_file`: Read the contents of a file to find answers

Instructions:
1. Use `list_files` first to explore the 'wiki' directory and see what documentation exists
2. Use `read_file` to examine relevant files and find the answer
3. When you find the answer, include the source reference in the format: `wiki/filename.md#section`
4. Format your final answer exactly as:
   ANSWER: <your answer>
   SOURCE: <source reference>

You can make up to 10 tool calls. Be efficient - try to find the answer with minimal calls.
"""
```

## Output Format

The agent outputs a single JSON line to stdout:

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\napi.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git Workflow\n\n## Resolving Merge Conflicts\n..."
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's final answer to the question |
| `source` | string | Wiki section reference (e.g., `wiki/git-workflow.md#section`) |
| `tool_calls` | array | All tool calls made during the agentic loop |

### Tool Call Entry

Each entry in `tool_calls` contains:

| Field | Type | Description |
|-------|------|-------------|
| `tool` | string | Name of the tool called |
| `args` | object | Arguments passed to the tool |
| `result` | string | Tool's return value (file contents or error message) |

All debug/progress output goes to **stderr**.

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI agent with tools and agentic loop |
| `.env.agent.secret` | LLM credentials (gitignored) |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `AGENT.md` | This documentation |
| `wiki/` | Documentation files the agent can read |

## Usage

```bash
# Run with uv
uv run agent.py "How do you resolve a merge conflict?"

# Or run directly with Python
python3 agent.py "How do you resolve a merge conflict?"
```

### Example Output

```bash
$ uv run agent.py "How do you resolve a merge conflict?"
🤖 Processing: How do you resolve a merge conflict?
Using model: qwen3-coder-plus
API base: http://10.93.25.217:42005/v1

🔄 Loop 1/10
  🤔 LLM requested 1 tool(s)
  🔧 Executing: list_files({'path': 'wiki'})

🔄 Loop 2/10
  🤔 LLM requested 1 tool(s)
  🔧 Executing: read_file({'path': 'wiki/git-workflow.md'})

🔄 Loop 3/10
✅ Final response received
{"answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.", "source": "wiki/git-workflow.md#resolving-merge-conflicts", "tool_calls": [...]}
```

## Environment Configuration

Create `.env.agent.secret` from `.env.agent.example`:

```bash
cp .env.agent.example .env.agent.secret
```

Edit `.env.agent.secret`:

```env
LLM_API_KEY=your-api-key-here
LLM_API_BASE=http://10.93.25.217:42005/v1
LLM_MODEL=qwen3-coder-plus
```

## Error Handling

- **Missing environment file:** Exit code 1, error to stderr
- **Missing environment variables:** Exit code 1, error to stderr
- **Network errors:** Exit code 1, error to stderr
- **API errors (4xx/5xx):** Exit code 1, error to stderr
- **Timeout (>60s):** Exit code 1, error to stderr
- **Path traversal attempt:** Tool returns error message (not thrown)
- **File not found:** Tool returns error message (not thrown)
- **Max tool calls reached:** Returns partial answer with warning to stderr

## Testing

Run the regression tests:

```bash
uv run pytest backend/tests/unit/test_agent.py -v
```

Or run manually:

```bash
# Test basic functionality
python3 agent.py "What is 2+2?" | jq .

# Test tool calling
python3 agent.py "What files are in the wiki?" | jq .
```

## Future Work (Task 3)

- **Task 3:** Add more tools (`query_api`, `search_code`) and extend the agentic loop to query the backend API and search code files.
