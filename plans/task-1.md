# Task 1 Plan: Call an LLM from Code

## LLM Provider and Model

- **Provider:** Qwen Code API (self-hosted on VM via qwen-code-oai-proxy)
- **Model:** `qwen3-coder-plus`
- **API Base:** `http://10.93.25.217:42005/v1` (OpenAI-compatible endpoint)
- **Authentication:** API key stored in `.env.agent.secret` (not hardcoded)

## Architecture

The agent is a simple CLI program with the following flow:

```
CLI input (question) → Parse argument → Call LLM API → Parse response → Output JSON
```

### Components

1. **Environment Loading**
   - Read `.env.agent.secret` for `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
   - Use `pydantic-settings` or manual parsing (project already uses `pydantic-settings`)

2. **LLM Client**
   - Use `httpx` (already in project dependencies) to make HTTP POST requests
   - Endpoint: `{LLM_API_BASE}/chat/completions`
   - Request format (OpenAI-compatible):
     ```json
     {
       "model": "qwen3-coder-plus",
       "messages": [{"role": "user", "content": "<question>"}]
     }
     ```
   - Headers: `Authorization: Bearer <LLM_API_KEY>`, `Content-Type: application/json`

3. **Response Parsing**
   - Extract `choices[0].message.content` from the API response
   - Format output as JSON: `{"answer": "<content>", "tool_calls": []}`

4. **Output Handling**
   - **stdout:** Only valid JSON (single line)
   - **stderr:** All debug/progress messages (using `print(..., file=sys.stderr)`)
   - Exit code 0 on success

## Error Handling

- **Timeout:** 60 seconds for the API call (using `httpx` timeout)
- **Network errors:** Log to stderr, exit with non-zero code
- **API errors (4xx/5xx):** Log to stderr, exit with non-zero code
- **Missing env vars:** Log to stderr, exit with non-zero code

## Data Flow

```
1. Parse sys.argv[1] as the question
2. Load environment variables from .env.agent.secret
3. Build HTTP request to LLM API
4. Send request with timeout=60
5. Parse JSON response
6. Extract answer text
7. Print {"answer": "...", "tool_calls": []} to stdout
```

## Testing Strategy

- One regression test that:
  - Runs `agent.py` as a subprocess with a sample question
  - Parses stdout as JSON
  - Checks that `answer` field exists and is non-empty
  - Checks that `tool_calls` field exists and is an array

## Files to Create

1. `plans/task-1.md` — This plan
2. `agent.py` — The CLI agent
3. `.env.agent.secret` — Environment configuration (gitignored)
4. `AGENT.md` — Documentation
5. `backend/tests/unit/test_agent.py` or `tests/test_agent.py` — Regression test
