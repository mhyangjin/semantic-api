# Coding Guide

## Python

- Python 3.12
- Async first
- Pydantic v2
- Type hints required

---

## Architecture

Business Logic

↓

Semantic Layer

↓

LLM

↓

Athena

---

## LLM

The LLM client only communicates with SageMaker.

Prompt generation belongs in prompt.py.

Business logic never belongs in LLMClient.

---

## Semantic Layer

Semantic Layer never generates SQL.

Semantic Layer never executes SQL.

---

## Testing

Every new MCP Tool must have a demo test.

Every public API should have type hints.

Every model should use Pydantic.