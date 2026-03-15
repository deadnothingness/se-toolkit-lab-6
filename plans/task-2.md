# Task 2: The Documentation Agent - Implementation Plan

## Overview
Extend the basic LLM caller from Task 1 with two tools (`read_file`, `list_files`) and an agentic loop that allows the LLM to explore the project wiki and answer questions with source references.

## Tool Definitions

### `list_files`
- **Description:** List files and directories at a given path relative to project root
- **Parameters:**
  - `path` (string) - directory path (must not escape project root)
- **Returns:** Newline-separated list of entries, or error message
- **Security:** Validate path with `is_path_safe()` to prevent `../` traversal

### `read_file`
- **Description:** Read contents of a file at given path
- **Parameters:**
  - `path` (string) - file path relative to project root
- **Returns:** File contents as string, or error message
- **Security:** Validate path; only allow files (not directories)

## Agentic Loop Design

1. **Initial call:** Send system prompt + user question + tool schemas
2. **If `tool_calls` present:**
   - Execute each tool safely
   - Append results as `tool` role messages
   - Go to step 1 (max 10 iterations)
3. **If no tool calls:**
   - Extract answer from final message
   - Parse source from response (format: `filename.md#section`)
   - Return JSON with answer, source, and all tool calls

## System Prompt Strategy
Tell the LLM:
- To use `list_files` to discover wiki structure
- To use `read_file` to examine relevant files
- To include source reference in format `wiki/filename.md#section`
- That it can make multiple tool calls
- Maximum 10 tool calls per conversation

## Output Format
```json
{
  "answer": "string",
  "source": "wiki/filename.md#section",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
