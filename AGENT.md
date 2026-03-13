# Agent Architecture

## Overview

This project implements a CLI agent (`agent.py`) that answers questions by calling an LLM API. The agent is the foundation for a more advanced agent with tools and agentic loop in subsequent tasks.

## LLM Provider

- **Provider:** Qwen Code API (self-hosted via `qwen-code-oai-proxy`)
- **Model:** `qwen3-coder-plus`
- **API Compatibility:** OpenAI-compatible chat completions API
- **Daily Limit:** 1000 free requests per day

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  CLI Input      │────▶│  agent.py    │────▶│  LLM API        │────▶│  JSON Output │
│  (question)     │     │  (parser)    │     │  (qwen3-coder)  │     │  (answer)    │
└─────────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
```

### Data Flow

1. **Input Parsing:** The agent reads the question from `sys.argv[1]`
2. **Environment Loading:** Reads `.env.agent.secret` for API credentials
3. **API Call:** Makes HTTP POST to `{LLM_API_BASE}/chat/completions`
4. **Response Parsing:** Extracts `choices[0].message.content` from the response
5. **Output:** Prints JSON `{"answer": "...", "tool_calls": []}` to stdout

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI agent |
| `.env.agent.secret` | LLM credentials (gitignored) |
| `plans/task-1.md` | Implementation plan |
| `AGENT.md` | This documentation |

## Usage

```bash
# Run with uv
uv run agent.py "What does REST stand for?"

# Or run directly with Python
python3 agent.py "What does REST stand for?"
```

### Output Format

The agent outputs a single JSON line to stdout:

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

- `answer`: The LLM's response text
- `tool_calls`: Empty array (populated in Task 2 when tools are added)

All debug/progress output goes to **stderr**.

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

## Testing

Run the regression test:

```bash
uv run pytest backend/tests/unit/test_agent.py -v
```

Or run manually:

```bash
python3 agent.py "What is 2+2?" | jq .
```

## Future Work (Tasks 2-3)

- **Task 2:** Add tools (file read, API query, etc.)
- **Task 3:** Implement agentic loop with tool calling
