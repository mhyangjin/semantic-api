# Semantic Layer MCP Server

자연어 데이터 질의를 SQL 생성에 필요한 semantic context로 변환하는 메타데이터 기반 MCP 서버입니다.

일반 사용자는 데이터베이스 구조를 몰라도 비즈니스 용어로 질문할 수 있습니다. 사내 Agent는 LLM으로 질문을 구조화한 뒤 이 MCP에서 metric, dimension, filter, 테이블과 조인 정보를 조회하고, 그 결과를 이용해 SQL을 생성합니다.

이 프로젝트의 주목적은 **MCP Server**입니다. FastAPI 서버는 메타데이터 조회를 위한 보조 인터페이스로 제공합니다.

## 처리 흐름

1. 사용자가 자연어로 질문합니다.
2. 사내 Agent가 LLM을 이용해 질문을 metric, dimension, filter 등으로 구조화합니다.
3. Agent가 구조화된 요청으로 MCP의 `build_context`를 호출합니다.
4. MCP가 필요한 metric 정의, dimension mapping, filter, 테이블과 조인을 반환합니다.
5. Agent가 이 context를 LLM에 전달해 SQL을 생성합니다.
6. 사내 Agent가 SQL을 검증하고 내부 서비스를 통해 실행합니다.
7. 조회 결과를 사용자에게 반환합니다.

```text
사용자 → 사내 Agent → LLM(질문 구조화)
                    → Semantic MCP(메타데이터 해석)
                    → LLM(SQL 생성)
                    → 사내 검증 및 SQL 실행 → 사용자
```

## 주요 기능

- 비즈니스 용어와 alias를 canonical metric/dimension/filter로 해석
- Athena SQL 생성에 필요한 최소 context 제공
- base metric과 derived metric 의존성 해석
- dimension별 물리 테이블, 컬럼 및 변환식 제공
- 날짜 범위와 literal filter 해석
- 요청에 필요한 테이블과 조인만 선별
- YAML 메타데이터를 통한 확장
- MCP 외에 보조 FastAPI 인터페이스 제공

## 빠른 시작

### 요구 사항

- Python 3.12 이상
- pip, Poetry 또는 uv

### 설치

```bash
git clone <repository-url>
cd semantic-api
pip install -r requirements.txt
```

### MCP Server 실행

```bash
python -m mcp_server.server
```

기본 transport는 `streamable-http`, host는 `0.0.0.0`, port는 `8000`입니다.

Docker로 실행하려면 다음 명령을 사용합니다.

```bash
docker compose up -d semantic-mcp
docker compose logs -f semantic-mcp
```

Docker Compose에서는 호스트의 `8092` 포트가 MCP 컨테이너의 `8000` 포트로 연결됩니다.

## MCP 도구

| 도구 | 용도 |
| --- | --- |
| `build_context` | SQL 생성에 필요한 전체 semantic context를 한 번에 구성하는 기본 도구 |
| `search_glossary` | 미인식 용어와 유사한 canonical 후보 검색 |
| `resolve_semantics` | metric, dimension, filter, analysis, pattern 해석 |
| `get_metric` | metric 상세 조회 |
| `get_dimension` | dimension 상세 조회 |
| `get_table` | 테이블과 조인 정보 조회 |
| `get_pattern` | 분석 pattern 해석 결과 조회 |

SQL을 생성할 때는 여러 조회 도구를 순차 호출하기보다 `build_context`를 우선 사용합니다. 자유 입력값은 `literal_filters`에 구조화해 전달하고, `filters`에는 glossary에 등록된 용어만 전달합니다.

### `build_context` 요청 예시

```json
{
  "request": {
    "metrics": ["발송 성공률"],
    "dimensions": ["채널"],
    "filters": ["지난 달"],
    "literal_filters": [
      {"dimension": "organization", "operator": "=", "value": "sample_team_01"}
    ],
    "analysis": [],
    "patterns": [],
    "question": "지난달 조직 sample_team_01의 채널별 발송 성공률을 알려줘"
  }
}
```

`question`을 함께 전달하면 dimension YAML의 `literal_patterns`에 따라 자유 입력값을 추출합니다. 새 literal 규칙은 Python에 하드코딩하지 않고 metadata에 선언합니다.

## 메타데이터

```text
metadata/
├── table/       물리 테이블, 컬럼, 조인
├── dimension/   분석 차원, mapping, literal pattern
├── metric/      base/derived metric
├── glossary/    비즈니스 용어와 alias
├── pattern/     재사용 가능한 분석 pattern
└── schema/      metadata schema
```

업무 용어, 테이블 구조, 추출 정규식, prefix와 연관 filter 같은 변경 가능한 규칙은 YAML에 선언합니다. 새로운 사례를 지원하기 위해 서비스 코드에 특정 문자열이나 dimension ID를 추가하지 않습니다. 기존 모델로 표현할 수 없는 경우에는 개별 예외 처리보다 재사용 가능한 metadata schema와 범용 resolver를 먼저 확장합니다.

### 다른 프로젝트에 적용할 때

이 저장소의 metadata는 예제 발송 시스템의 데이터 모델입니다. 다른 시스템에 적용할 때는 다음 항목을 대상 프로젝트의 실제 데이터베이스 구조와 비즈니스 용어에 맞게 **반드시 수정해야 합니다**.

- `metadata/table/`: 테이블명, 컬럼명, 타입, 조인 조건과 cardinality
- `metadata/dimension/`: 물리 컬럼 mapping, 변환식, literal pattern
- `metadata/metric/`: 집계식, 기준 테이블, 지원 dimension
- `metadata/glossary/`: 사용자 용어, alias와 filter
- `metadata/pattern/`: 분석 목적별 metric, dimension과 filter 조합

예제 metadata를 그대로 사용하면 잘못된 SQL, 누락된 데이터 또는 one-to-many 조인에 의한 중복 결과가 발생할 수 있습니다. 대상 프로젝트의 스키마를 애플리케이션 코드에 하드코딩하지 말고 metadata를 변경하십시오.

## 현재 예제 테이블 구조

공통 연결 키는 `notification_id`이며 `notification`을 중심으로 관련 테이블이 연결됩니다. 상세 정의의 기준은 `metadata/table/*.yaml`입니다.

| 테이블 | 역할 | 주요 컬럼 |
| --- | --- | --- |
| `notification` | 발송 요청 | `notification_id`, `info`, `request_channel_id`, `request_kst_date` |
| `notification_channels` | 채널 라우팅 | `notification_id`, `routing_priority`, `channel_id` |
| `notification_status` | 수신자별 처리 결과 | `notification_id`, `custom_message_id`, `status`, `result`, `error_code`, `error_message`, `occurred_at` |
| `notification_index` | 조건별 역색인 | `index`, `notification_id`, `occurred_at` |
| `recipient` | 발송 대상 | `recipient_id`, `notification_id`, `custom_message_id`, `channel_id`, `notification_type`, `organization_id`, `service_id`, `workspace_id` |
| `inbox` | 고객별 읽음 여부 | `customer_id`, `notification_id`, `channel_id`, `custom_message_id`, `is_open` |

### 주요 조인

| 기준 | 대상 | 조건 | Cardinality |
| --- | --- | --- | --- |
| `notification` | `notification_channels` | `notification_id = notification_id` | one-to-many |
| `notification` | `notification_index` | `notification_id = notification_id` | one-to-many |
| `notification` | `notification_status` | `notification_id = notification_id`; 필요 시 `request_channel_id = status` | one-to-many |
| `notification` | `recipient` | `notification_id = notification_id` | one-to-many, entity many-to-many |
| `notification` | `inbox` | `notification_id = notification_id` | one-to-many |
| `notification_channels` | `notification_status` | `notification_id = notification_id`; 필요 시 `channel_id = status` | one-to-many |
| `notification_status` | `recipient` | `notification_id`와 `custom_message_id` 일치 | many-to-one |

`notification_index.index`는 조회 종류에 따라 `EVENT#`, `CH#`, `OR#`, `WS#`, `TEMP#`, `JOB#`, `SOURCE:` 등의 prefix를 사용합니다.

## 보안 경계

이 구조의 핵심 장점은 외부 LLM에 데이터베이스 자격 증명이나 직접 접속 권한을 제공하지 않고, 실제 SQL 실행과 데이터 조회를 사내 Agent 및 내부 서비스로 제한할 수 있다는 점입니다. 외부 LLM은 SQL을 제안하지만 데이터베이스에 직접 연결하거나 쿼리를 실행할 수 없어야 합니다.

다만 내부 정보의 비노출이 자동으로 보장되지는 않습니다. 사용자의 자연어 질문과 질문값, MCP가 반환한 테이블·컬럼·조인 metadata, 생성 SQL 및 LLM에 다시 전달한 조회 결과는 외부 LLM에 노출될 수 있습니다. LLM 서비스의 데이터 보존·학습 정책과 기업용 계약 조건을 검토하고 전송 정보를 최소화해야 합니다.

### 사내 Agent 보호장치

- DB 자격 증명을 prompt, MCP 응답 또는 외부 로그에 포함하지 않습니다.
- 읽기 전용 최소 권한 계정으로 SQL을 실행합니다.
- 접근 가능한 catalog, schema, table과 column에 allowlist를 적용합니다.
- SQL을 parser/AST로 검사하고 승인된 `SELECT`만 허용합니다.
- DDL, DML, 권한 변경, 관리 명령, 다중 statement와 우회성 주석을 차단합니다.
- 실행 시 사용자 권한을 다시 확인하고 row/column-level security를 적용합니다.
- 최대 행 수, 실행 시간, 스캔 용량, 동시 실행 수와 비용을 제한합니다.
- 민감한 질문값은 LLM 전송 전에 마스킹 또는 토큰화합니다.
- 조회 결과는 외부 LLM에 보내지 않거나 집계·마스킹한 최소 결과만 전달합니다.
- 질문, SQL, 검증 결과, 실행 사용자와 결과를 감사 로그로 남기되 민감정보는 마스킹합니다.
- 모든 LLM 생성 SQL을 신뢰하지 않는 입력으로 취급합니다.

이 MCP는 semantic metadata와 SQL 생성 context를 제공합니다. 실행 통제는 MCP를 호출하고 SQL을 실행하는 사내 Agent 및 내부 서비스에서 구현해야 합니다.

## 보조 FastAPI 서버

```bash
python main.py
# 또는
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

Docker Compose에서는 `semantic-api` 서비스가 호스트의 `8091` 포트에 연결됩니다.

```bash
docker compose up -d semantic
```

주요 endpoint:

- `GET /system`
- `GET /system/health`
- `POST /semantic/query`

## 프로젝트 구조

```text
semantic-api/
├── mcp_server/        MCP server, tools와 요청/응답 model
├── app/semantic/      metadata loader, repository, resolver와 service
├── metadata/          table, dimension, metric, glossary와 pattern
├── tests/             semantic context 회귀 테스트
├── apis/              보조 FastAPI endpoint
├── main.py            FastAPI entrypoint
├── Dockerfile.mcp     MCP image
├── Dockerfile.api     API image
└── docker-compose.yml
```

## 테스트

```bash
PYTHONPATH=. pytest
```

## 문의

julu1@naver.com

## 라이선스

MIT License

```text
Copyright (c) 2026 julu1

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
