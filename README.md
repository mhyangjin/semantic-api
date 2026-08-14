# Semantic API

[한국어](#한국어) | [English](#english)

---

## 한국어

### 프로젝트 소개

**Semantic API**는 의미 기반의 데이터 분석 및 조회 기능을 제공하는 FastAPI 기반 REST API 서버입니다. 
복잡한 데이터 구조를 간단하고 직관적인 API 인터페이스로 제공하며, YAML 기반의 메타데이터를 통해 유연하고 확장 가능한 구조를 구현하고 있습니다.

### 주요 기능

- **System API**: 서버 상태 확인 및 헬스 체크
- **Semantic API**: 의미 기반 데이터 조회 및 분석
- **MCP Server**: Model Context Protocol 기반 도구 제공
- **메타데이터 관리**: YAML 기반의 다양한 메타데이터 정의
  - **Dimension**: 차원 정의 (채널, 고객, 조직 등)
  - **Metric**: 메트릭 정의 (기본 메트릭, 파생 메트릭)
  - **Pattern**: 분석 패턴 (고객 피로도 분석 등)
  - **Schema**: 테이블 구조 정의
  - **Table**: 메인 데이터 테이블 정의
- **CORS 지원**: 다중 오리진 접근 허용
- **JSON 로깅**: 구조화된 로깅으로 모니터링 용이

### 프로젝트 장점

- **도메인 친화적 질의 해석**: 비즈니스 용어를 메트릭/차원/테이블 메타데이터로 변환해 분석 진입 장벽을 낮춥니다.
- **메타데이터 중심 확장성**: 코드 수정 없이 YAML 추가/변경만으로 분석 대상과 용어를 빠르게 확장할 수 있습니다.
- **API + MCP 동시 제공**: REST API와 MCP 도구를 함께 제공해 웹 서비스와 AI 에이전트 환경을 모두 지원합니다.
- **운영 편의성**: Docker Compose, CORS, JSON 구조화 로그를 기본 제공해 배포와 모니터링을 단순화합니다.
- **모듈화된 구조**: loader/resolver/service/repository 계층 분리로 유지보수성과 테스트 용이성을 높였습니다.

### 기술 스택

- **Framework**: FastAPI 0.140.7
- **Python**: 3.12+
- **Server**: Uvicorn 0.51.0
- **Database**: SQLAlchemy 2.0.51, PostgreSQL
- **Data Validation**: Pydantic 2.13.4
- **Logging**: JSON 로깅, Colorlog
- **MCP**: FastMCP 3.4.5
- **Others**: PyYAML, httpx, aiohttp

### 설치

#### 필수 조건

- Python 3.12 이상
- pip 또는 uv 패키지 매니저

#### 로컬 설치

```bash
# 저장소 클론
git clone <repository-url>
cd semantic-api

# 의존성 설치
pip install -r requirements.txt

# 또는 uv 사용
uv pip install -r requirements.txt
```

#### Docker를 통한 설치

```bash
# Docker Compose를 사용한 빌드 및 실행 (API + MCP)
docker-compose up -d

# 또는 Docker CLI 사용 (API)
docker build -f Dockerfile.api -t semantic-api .
docker run -d -p 8091:8080 --name semantic-api semantic-api

# Docker CLI 사용 (MCP)
docker build -f Dockerfile.mcp -t semantic-mcp .
docker run -d -p 8092:8000 --name semantic-mcp semantic-mcp
```

### 사용 방법

#### 로컬 실행

```bash
# 개발 서버 실행 (핫 리로드 활성화)
python main.py

# 또는 uvicorn 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

#### Docker 실행

```bash
# Docker Compose로 실행
docker-compose up -d

# 서비스 중지
docker-compose down

# 로그 확인
docker-compose logs -f semantic-api
docker-compose logs -f semantic-mcp
```

#### API 접근

- **로컬 API**: http://localhost:8080
- **Docker API**: http://localhost:8091
- **Docker MCP (streamable-http)**: http://localhost:8092

#### MCP Server로 사용하기

현재 코드 기준으로 MCP 엔트리포인트는 `mcp/server.py`이며, 아래처럼 실행할 수 있습니다.

```bash
# 방법 1: 모듈 실행
python -m mcp.server

# 방법 2: 파일 직접 실행
python mcp/server.py
```

MCP 클라이언트(예: Claude Desktop, Cursor, 기타 MCP 호환 클라이언트)에서 STDIO 서버로 등록할 때는 아래처럼 설정할 수 있습니다.

```json
{
  "mcpServers": {
    "semantic-layer": {
      "command": "python",
      "args": ["-m", "mcp.server"],
      "cwd": "/absolute/path/to/semantic-api"
    }
  }
}
```

제공되는 주요 MCP 도구:

- `resolve_query`: 비즈니스 용어를 메타데이터(metric/dimension/table/filter)로 해석
- `get_metric`: 메트릭 상세 메타데이터 조회
- `get_dimension`: 차원 상세 메타데이터 조회
- `get_table`: 테이블 상세 메타데이터 조회
- `get_pattern`: 분석 패턴 해석 결과 조회

### 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하여 다음과 같이 설정할 수 있습니다:

```env
PROJECT_NAME=semantic-api
ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8080
VERSION=0.1.0
LOGGER_LOGLEVEL=INFO
UVICORN_RELOAD=True
UVICORN_WORKERS=1
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
```

### 프로젝트 구조

```
semantic-api/
├── main.py                    # 애플리케이션 진입점
├── requirements.txt           # Python 의존성
├── pyproject.toml            # 프로젝트 메타데이터
├── Dockerfile                # Docker 이미지 빌드 설정
├── docker-compose.yml        # Docker Compose 설정
├── .dockerignore              # Docker 빌드 제외 파일
│
├── app/                       # 애플리케이션 핵심 로직
│   ├── core/                 # 핵심 설정 및 로깅
│   │   ├── config.py         # 환경 설정
│   │   └── logger/           # 로깅 설정
│   └── semantic/             # 의미 관련 로직
│       ├── loader.py         # 메타데이터 로더
│       ├── models.py         # 데이터 모델
│       ├── repository.py      # 데이터베이스 접근 계층
│       ├── resolver.py        # 의미 해석기
│       └── service.py         # 비즈니스 로직
│
├── apis/                      # REST API 엔드포인트
│   ├── system/               # 시스템 관련 API
│   │   ├── api/v1.py         # v1 엔드포인트
│   │   ├── models.py         # 데이터 모델
│   │   ├── schemas.py        # 요청/응답 스키마
│   │   └── crud.py           # 데이터베이스 작업
│   └── semantic/             # 의미 관련 API
│       ├── api/v1.py         # v1 엔드포인트
│       ├── request.py        # 요청 모델
│       └── response.py       # 응답 모델
│
├── mcp/                       # MCP 서버
│   ├── server.py             # MCP 서버 메인
│   ├── tools.py              # MCP 도구 정의
│   └── models.py             # MCP 데이터 모델
│
└── metadata/                  # 메타데이터 정의
    ├── dimension/            # 차원 정의 (YAML)
    ├── metric/               # 메트릭 정의 (YAML)
    ├── pattern/              # 패턴 정의 (YAML)
    ├── table/                # 테이블 정의 (YAML)
    ├── glossary/             # 용어 정의 (YAML)
    └── schema/               # 스키마 정의 (JSON)
```

### API 엔드포인트

#### System API
- `GET /system/health` - 서버 상태 확인

#### Semantic API
- `GET /semantic/dimensions` - 이용 가능한 차원 조회
- `GET /semantic/metrics` - 이용 가능한 메트릭 조회
- `GET /semantic/tables` - 이용 가능한 테이블 조회
- `POST /semantic/query` - 의미 기반 데이터 조회

### 메타데이터 작성 가이드

#### 차원 (Dimension) 정의
`metadata/dimension/` 디렉토리에 YAML 파일로 차원을 정의합니다:

```yaml
# metadata/dimension/customer.yaml
name: customer
display_name: 고객
description: 고객 정보
type: dimension
fields:
  - name: customer_id
    type: string
    description: 고객 ID
  - name: customer_name
    type: string
    description: 고객 이름
```

#### 메트릭 (Metric) 정의
`metadata/metric/` 디렉토리에 YAML 파일로 메트릭을 정의합니다:

```yaml
# metadata/metric/base/request_count.yaml
name: request_count
display_name: 요청 수
description: 총 요청 수
type: metric
aggregation: sum
source_table: notification
```

### 로깅

프로젝트는 JSON 형식의 구조화된 로깅을 지원합니다. 로그 레벨은 환경 변수로 설정됩니다:

```bash
# 로그 레벨 설정
export LOGGER_LOGLEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### 테스트

```bash
# pytest를 사용한 테스트 실행
pytest

# 커버리지와 함께 테스트 실행
pytest --cov
```

### 배포

#### 프로덕션 설정

Docker Compose 파일에서 환경 변수를 수정하여 프로덕션 설정을 적용할 수 있습니다:

```yaml
environment:
  - ENV=production
  - UVICORN_RELOAD=False
  - UVICORN_WORKERS=4
  - LOGGER_LOGLEVEL=WARNING
```

#### 핸들리 배포 체크리스트

- [ ] `.env` 파일 설정 (프로덕션 값)
- [ ] 데이터베이스 연결 확인
- [ ] CORS 설정 검토
- [ ] 로그 레벨 설정 (INFO 또는 WARNING)
- [ ] Uvicorn 워커 수 조정
- [ ] 포트 설정 확인

### 트러블슈팅

#### 포트가 이미 사용 중인 경우

```bash
# 충돌하는 프로세스 확인
lsof -i :8080

# Docker 컨테이너 확인
docker ps
docker container ls
```

#### 의존성 문제

```bash
# 의존성 재설치
pip install --force-reinstall -r requirements.txt

# 캐시 삭제 후 설치
pip cache purge
pip install -r requirements.txt
```

#### 데이터베이스 연결 오류

- PostgreSQL 서버 실행 여부 확인
- 데이터베이스 자격증명 확인 (환경 변수)
- 데이터베이스 마이그레이션 실행 확인

### 기여

프로젝트에 기여하고 싶으시면:

1. 저장소를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/AmazingFeature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치를 푸시합니다 (`git push origin feature/AmazingFeature`)
5. Pull Request를 생성합니다

### 라이선스

[라이선스 유형 명시]

### 문의

질문이나 제안사항이 있으시면 이슈를 등록해주세요.

---

## English

### Project Introduction

**Semantic API** is a FastAPI-based REST API server that provides semantic-based data analysis and query functionality.
It offers complex data structures through simple and intuitive API interfaces, implementing flexible and extensible structures through YAML-based metadata.

### Key Features

- **System API**: Server status checking and health checks
- **Semantic API**: Semantic-based data query and analysis
- **MCP Server**: Tools provided based on Model Context Protocol
- **Metadata Management**: Various metadata definitions based on YAML
  - **Dimension**: Dimension definitions (channels, customers, organizations, etc.)
  - **Metric**: Metric definitions (base metrics, derived metrics)
  - **Pattern**: Analysis patterns (customer fatigue analysis, etc.)
  - **Schema**: Table structure definitions
  - **Table**: Main data table definitions
- **CORS Support**: Multiple origin access allowed
- **JSON Logging**: Structured logging for easy monitoring

### Project Advantages

- **Domain-friendly query resolution**: Converts business terms into metric/dimension/table metadata, lowering the barrier to analytics.
- **Metadata-first extensibility**: You can expand analysis scope and vocabulary quickly by editing YAML, without frequent code changes.
- **API and MCP support together**: Provides both REST endpoints and MCP tools for web services and AI agent workflows.
- **Operational simplicity**: Built-in Docker Compose setup, CORS support, and structured JSON logs make deployment and monitoring easier.
- **Modular architecture**: Clear separation of loader/resolver/service/repository layers improves maintainability and testability.

### Technology Stack

- **Framework**: FastAPI 0.140.7
- **Python**: 3.12+
- **Server**: Uvicorn 0.51.0
- **Database**: SQLAlchemy 2.0.51, PostgreSQL
- **Data Validation**: Pydantic 2.13.4
- **Logging**: JSON logging, Colorlog
- **MCP**: FastMCP 3.4.5
- **Others**: PyYAML, httpx, aiohttp

### Installation

#### Prerequisites

- Python 3.12 or higher
- pip or uv package manager

#### Local Installation

```bash
# Clone the repository
git clone <repository-url>
cd semantic-api

# Install dependencies
pip install -r requirements.txt

# Or using uv
uv pip install -r requirements.txt
```

#### Installation via Docker

```bash
# Build and run using Docker Compose (API + MCP)
docker-compose up -d

# Or using Docker CLI (API)
docker build -f Dockerfile.api -t semantic-api .
docker run -d -p 8091:8080 --name semantic-api semantic-api

# Docker CLI (MCP)
docker build -f Dockerfile.mcp -t semantic-mcp .
docker run -d -p 8092:8000 --name semantic-mcp semantic-mcp
```

### Usage

#### Local Execution

```bash
# Run development server (with hot reload)
python main.py

# Or run uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

#### Docker Execution

```bash
# Run with Docker Compose
docker-compose up -d

# Stop the service
docker-compose down

# View logs
docker-compose logs -f semantic-api
docker-compose logs -f semantic-mcp
```

#### API Access

- **Local API**: http://localhost:8080
- **Docker API**: http://localhost:8091
- **Docker MCP (streamable-http)**: http://localhost:8092

#### Using as an MCP Server

Based on the current code, the MCP entry point is `mcp/server.py`, and you can run it as follows.

```bash
# Option 1: run as a module
python -m mcp.server

# Option 2: run the file directly
python mcp/server.py
```

When registering this as a STDIO server in an MCP client (for example, Claude Desktop, Cursor, or other MCP-compatible clients), you can use a config like this.

```json
{
  "mcpServers": {
    "semantic-layer": {
      "command": "python",
      "args": ["-m", "mcp.server"],
      "cwd": "/absolute/path/to/semantic-api"
    }
  }
}
```

Main MCP tools provided:

- `resolve_query`: Resolve business terms into metric/dimension/table/filter metadata
- `get_metric`: Get detailed metadata for a metric
- `get_dimension`: Get detailed metadata for a dimension
- `get_table`: Get detailed metadata for a table
- `get_pattern`: Get resolved metadata for an analysis pattern

### Environment Variables

Create a `.env` file in the project root and configure as follows:

```env
PROJECT_NAME=semantic-api
ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8080
VERSION=0.1.0
LOGGER_LOGLEVEL=INFO
UVICORN_RELOAD=True
UVICORN_WORKERS=1
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
```

### Project Structure

```
semantic-api/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── pyproject.toml            # Project metadata
├── Dockerfile                # Docker image build configuration
├── docker-compose.yml        # Docker Compose configuration
├── .dockerignore              # Docker build exclusion files
│
├── app/                       # Application core logic
│   ├── core/                 # Core configuration and logging
│   │   ├── config.py         # Environment configuration
│   │   └── logger/           # Logging configuration
│   └── semantic/             # Semantic-related logic
│       ├── loader.py         # Metadata loader
│       ├── models.py         # Data models
│       ├── repository.py      # Database access layer
│       ├── resolver.py        # Semantic resolver
│       └── service.py         # Business logic
│
├── apis/                      # REST API endpoints
│   ├── system/               # System-related API
│   │   ├── api/v1.py         # v1 endpoints
│   │   ├── models.py         # Data models
│   │   ├── schemas.py        # Request/Response schemas
│   │   └── crud.py           # Database operations
│   └── semantic/             # Semantic-related API
│       ├── api/v1.py         # v1 endpoints
│       ├── request.py        # Request models
│       └── response.py       # Response models
│
├── mcp/                       # MCP Server
│   ├── server.py             # MCP server main
│   ├── tools.py              # MCP tool definitions
│   └── models.py             # MCP data models
│
└── metadata/                  # Metadata definitions
    ├── dimension/            # Dimension definitions (YAML)
    ├── metric/               # Metric definitions (YAML)
    ├── pattern/              # Pattern definitions (YAML)
    ├── table/                # Table definitions (YAML)
    ├── glossary/             # Glossary definitions (YAML)
    └── schema/               # Schema definitions (JSON)
```

### API Endpoints

#### System API
- `GET /system/health` - Check server status

#### Semantic API
- `GET /semantic/dimensions` - Retrieve available dimensions
- `GET /semantic/metrics` - Retrieve available metrics
- `GET /semantic/tables` - Retrieve available tables
- `POST /semantic/query` - Semantic-based data query

### Metadata Definition Guide

#### Dimension Definition
Define dimensions in the `metadata/dimension/` directory as YAML files:

```yaml
# metadata/dimension/customer.yaml
name: customer
display_name: Customer
description: Customer information
type: dimension
fields:
  - name: customer_id
    type: string
    description: Customer ID
  - name: customer_name
    type: string
    description: Customer Name
```

#### Metric Definition
Define metrics in the `metadata/metric/` directory as YAML files:

```yaml
# metadata/metric/base/request_count.yaml
name: request_count
display_name: Request Count
description: Total number of requests
type: metric
aggregation: sum
source_table: notification
```

### Logging

The project supports structured logging in JSON format. Log level is set via environment variable:

```bash
# Set log level
export LOGGER_LOGLEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Testing

```bash
# Run tests with pytest
pytest

# Run tests with coverage
pytest --cov
```

### Deployment

#### Production Configuration

You can apply production settings by modifying environment variables in the Docker Compose file:

```yaml
environment:
  - ENV=production
  - UVICORN_RELOAD=False
  - UVICORN_WORKERS=4
  - LOGGER_LOGLEVEL=WARNING
```

#### Deployment Checklist

- [ ] Configure `.env` file (production values)
- [ ] Verify database connection
- [ ] Review CORS settings
- [ ] Configure log level (INFO or WARNING)
- [ ] Adjust Uvicorn worker count
- [ ] Verify port configuration

### Troubleshooting

#### Port Already in Use

```bash
# Check conflicting process
lsof -i :8080

# Check Docker containers
docker ps
docker container ls
```

#### Dependency Issues

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Clear cache and install
pip cache purge
pip install -r requirements.txt
```

#### Database Connection Error

- Verify PostgreSQL server is running
- Check database credentials (environment variables)
- Verify database migration has been executed

### Contributing

To contribute to the project:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

## 작성자

문의 / 제안: julu1@naver.com

## 라이센스

MIT License

```
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
