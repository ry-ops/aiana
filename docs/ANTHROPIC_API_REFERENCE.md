# Anthropic API Reference

This document provides a reference for the Anthropic API relevant to Aiana development.

## API Overview

The Anthropic API provides programmatic access to Claude models via REST endpoints.

**Base URL**: `https://api.anthropic.com`

## Authentication

### API Keys

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json"
```

### Required Headers

| Header | Value | Description |
|--------|-------|-------------|
| `x-api-key` | Your API key | Authentication |
| `anthropic-version` | `2023-06-01` | API version |
| `content-type` | `application/json` | Request format |

## Messages API

### Create Message

**Endpoint**: `POST /v1/messages`

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "max_tokens": 1024,
  "messages": [
    {
      "role": "user",
      "content": "Hello, Claude!"
    }
  ]
}
```

### Response Format

```json
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Hello! How can I help you today?"
    }
  ],
  "model": "claude-sonnet-4-5-20250929",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 10,
    "output_tokens": 25
  }
}
```

### Available Models

| Model | ID | Context | Best For |
|-------|-----|---------|----------|
| Claude Opus 4.5 | `claude-opus-4-5-20251101` | 200K | Complex reasoning |
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | 200K | Balanced performance |
| Claude Haiku | `claude-3-5-haiku-20241022` | 200K | Fast responses |

## Streaming API

### Server-Sent Events (SSE)

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "stream": true,
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Event Types

```
event: message_start
data: {"type":"message_start","message":{...}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":25}}

event: message_stop
data: {"type":"message_stop"}
```

## Tool Use (Function Calling)

### Define Tools

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "max_tokens": 1024,
  "tools": [
    {
      "name": "get_weather",
      "description": "Get weather for a location",
      "input_schema": {
        "type": "object",
        "properties": {
          "location": {"type": "string"}
        },
        "required": ["location"]
      }
    }
  ],
  "messages": [{"role": "user", "content": "What's the weather in Tokyo?"}]
}
```

### Tool Use Response

```json
{
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lgs0",
      "name": "get_weather",
      "input": {"location": "Tokyo"}
    }
  ],
  "stop_reason": "tool_use"
}
```

### Tool Result

```json
{
  "messages": [
    {"role": "user", "content": "What's the weather in Tokyo?"},
    {"role": "assistant", "content": [{"type": "tool_use", ...}]},
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "toolu_01A09q90qw90lq917835lgs0",
          "content": "72°F, sunny"
        }
      ]
    }
  ]
}
```

## Rate Limits

### Default Limits

| Tier | Requests/min | Tokens/min | Tokens/day |
|------|-------------|------------|------------|
| Free | 5 | 20K | 100K |
| Build | 50 | 40K | 1M |
| Scale | 1000 | 400K | 50M |

### Rate Limit Headers

```
anthropic-ratelimit-requests-limit: 1000
anthropic-ratelimit-requests-remaining: 999
anthropic-ratelimit-requests-reset: 2025-01-01T00:00:00Z
anthropic-ratelimit-tokens-limit: 400000
anthropic-ratelimit-tokens-remaining: 399000
anthropic-ratelimit-tokens-reset: 2025-01-01T00:00:00Z
```

## Error Handling

### Error Response Format

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "max_tokens must be greater than 0"
  }
}
```

### Error Types

| Type | HTTP Code | Description |
|------|-----------|-------------|
| `invalid_request_error` | 400 | Invalid request parameters |
| `authentication_error` | 401 | Invalid API key |
| `permission_error` | 403 | API key lacks permission |
| `not_found_error` | 404 | Resource not found |
| `rate_limit_error` | 429 | Rate limit exceeded |
| `api_error` | 500 | Internal server error |
| `overloaded_error` | 529 | API overloaded |

## Python SDK

### Installation

```bash
pip install anthropic
```

### Basic Usage

```python
import anthropic

client = anthropic.Anthropic(api_key="your-api-key")

message = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude!"}
    ]
)

print(message.content[0].text)
```

### Streaming

```python
with client.messages.stream(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### Async Support

```python
import anthropic
import asyncio

async def main():
    client = anthropic.AsyncAnthropic()
    message = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(message.content[0].text)

asyncio.run(main())
```

## Message Batches API (Beta)

Process large batches asynchronously at 50% cost reduction.

### Create Batch

```python
batch = client.messages.batches.create(
    requests=[
        {
            "custom_id": "request-1",
            "params": {
                "model": "claude-sonnet-4-5-20250929",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": "Hello!"}]
            }
        }
    ]
)
```

### Check Status

```python
batch = client.messages.batches.retrieve(batch.id)
print(batch.processing_status)  # "in_progress", "ended"
```

## Files API (Beta)

Upload files for reference in messages.

```python
# Upload file
file = client.files.create(
    file=open("document.pdf", "rb"),
    purpose="user_data"
)

# Reference in message
message = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {"type": "file", "file_id": file.id},
            {"type": "text", "text": "Summarize this document"}
        ]
    }]
)
```

## Extended Thinking (Claude 4 Models)

```json
{
  "model": "claude-opus-4-5-20251101",
  "max_tokens": 16000,
  "thinking": {
    "type": "enabled",
    "budget_tokens": 10000
  },
  "messages": [{"role": "user", "content": "Solve this complex problem..."}]
}
```

## MCP Connector (Beta)

Connect to remote MCP servers directly from the API.

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "max_tokens": 1024,
  "mcp_servers": [
    {
      "type": "url",
      "url": "https://mcp.example.com",
      "name": "my-mcp-server"
    }
  ],
  "messages": [{"role": "user", "content": "Use the MCP tools"}]
}
```

## References

- [Anthropic API Documentation](https://docs.anthropic.com/en/api)
- [Python SDK Repository](https://github.com/anthropics/anthropic-sdk-python)
- [API Changelog](https://docs.claude.com/en/release-notes/api)
