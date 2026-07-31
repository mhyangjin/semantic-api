# Semantic Layer

## Purpose

The Semantic Layer converts business terminology into technical metadata.

Example

Business

```
발송 성공 건수
```

↓

Metric

```
send_success_count
```

---

Business

```
채널
```

↓

Dimension

```
channel
```

---

Business

```
지난달
```

↓

Filter

```
request_date BETWEEN ...
```

---

## MCP Tools

resolve_semantics()

Input

ResolveQueryRequest

Output

ResolveQueryResponse

---

get_metric()

Returns metric metadata.

---

get_dimension()

Returns dimension metadata.

---

get_table()

Returns table metadata.

---

get_pattern()

Returns pattern metadata.