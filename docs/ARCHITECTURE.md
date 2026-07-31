# Architecture

## Goal

Convert natural language into valid Athena SQL using a Semantic Layer.

```
User Question
        │
        ▼
      LLM
        │
        ▼
ResolveQueryRequest
        │
        ▼
Semantic Layer (MCP)
        │
        ▼
ResolveQueryResponse
        │
        ▼
      LLM
        │
        ▼
Athena SQL
        │
        ▼
Athena
```

## Components

### LLM

Responsibilities

- Understand natural language
- Build ResolveQueryRequest
- Generate Athena SQL

Never

- Invent metrics
- Invent dimensions
- Invent tables
- Invent joins

---

### Semantic Layer

Responsibilities

- Resolve glossary
- Resolve metrics
- Resolve dimensions
- Resolve filters
- Resolve patterns
- Return metadata

Never

- Generate SQL
- Execute SQL
- Interpret natural language

---

### Athena

Responsibilities

- Execute SQL only

---

## Source of Truth

The Semantic Layer is the only source of truth for metadata.