# IACS RAG Platform

문서 검색 플랫폼 (RAG - Retrieval Augmented Generation) 프로토타입

## 개요

이 프로젝트는 문서 업로드, 텍스트 추출, 벡터 임베딩 생성, 의미 기반 검색 및 LLM을 활용한 답변 생성 기능을 제공하는 RAG 플랫폼입니다.

## 주요 기능

- 📄 문서 업로드 및 파싱 (PDF, DOCX, 이메일)
- 🔍 텍스트 추출 및 청킹 처리
- 🧠 벡터 임베딩 생성 및 저장
- 🔎 의미 기반 문서 검색
- 💬 LLM을 활용한 답변 생성
- ⚡ 이벤트 기반 아키텍처

## 기술 스택

- **Backend**: FastAPI (Python 3.11+)
- **Database**: MongoDB (문서 저장)
- **Vector DB**: Qdrant (벡터 검색)
- **Message Queue**: Apache Kafka (이벤트 처리)
- **LLM**: OpenAI API
- **Package Manager**: uv

## 설치 및 실행

### 1. 환경 설정

```bash
# 가상환경 생성 및 활성화
uv venv iacsrag
source iacsrag/bin/activate

# 의존성 설치
uv pip install -e .
```

### 2. 인프라 서비스 실행

```bash
# Docker Compose로 MongoDB, Qdrant, Kafka 실행
docker-compose up -d
```

### 3. 환경 변수 설정

`.env.development` 파일에서 필요한 설정을 확인하고 수정하세요.

```bash
# OpenAI API 키 설정 (필수)
OPENAI_API_KEY=your-openai-api-key-here
```

### 4. 애플리케이션 실행

```bash
# 개발 서버 실행
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 프로젝트 구조

```
src/
├── core/                   # 핵심 설정 및 공통 모듈
├── infrastructure/         # 외부 시스템 연동
│   ├── database/          # MongoDB 연결
│   ├── vectordb/          # Qdrant 연결
│   └── messaging/         # Kafka 연결
├── modules/               # 비즈니스 모듈
│   ├── ingest/           # 문서 수집 모듈
│   ├── process/          # 문서 처리 모듈
│   ├── search/           # 검색 모듈
│   └── monitor/          # 모니터링 모듈
├── api/                  # REST API 엔드포인트
└── utils/                # 유틸리티 함수
```

## API 문서

애플리케이션 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 개발 가이드

### 테스트 실행

```bash
# 단위 테스트
pytest test/unit/

# 통합 테스트
pytest test/integration/

# 전체 테스트
pytest
```

### 모듈별 테스트 구조

#### 1. Core 모듈 테스트
- **소스 코드**: `src/core/`
- **테스트 파일**: `.clineignore/tests/test_core_*.py`
  - `test_core_config.py` - 설정 관리 테스트
  - `test_core_exceptions.py` - 예외 처리 테스트
  - `test_core_dependencies.py` - 의존성 주입 테스트
  - `test_core_logging.py` - 로깅 시스템 테스트

#### 2. Infrastructure 모듈 테스트
- **소스 코드**: `src/infrastructure/`
- **테스트 파일**: `.clineignore/tests/test_infrastructure_*.py`
  - `test_infrastructure_mongodb.py` - MongoDB 연결 테스트
  - `test_infrastructure_qdrant.py` - Qdrant 벡터DB 테스트
  - `test_infrastructure_kafka.py` - Kafka 메시징 테스트

#### 3. Utils 모듈 테스트
- **소스 코드**: `src/utils/`
- **테스트 파일**: `.clineignore/tests/test_utils_*.py`
  - `test_utils_id_generator.py` - ID 생성 유틸리티 테스트
  - `test_utils_hash.py` - 해시 함수 테스트
  - `test_utils_validators.py` - 검증 함수 테스트
  - `test_utils_datetime.py` - 날짜/시간 유틸리티 테스트

#### 4. Ingest 모듈 테스트
- **소스 코드**: `src/modules/ingest/`
- **테스트 파일**: `.clineignore/tests/test_ingest_*.py`
  - `test_ingest_domain_entities.py` - 도메인 엔티티 테스트
  - `test_ingest_infrastructure_document_repository.py` - 문서 저장소 테스트
  - `test_ingest_application_document_service.py` - 문서 서비스 테스트
  - `test_ingest_use_cases_parse_email.py` - 이메일 파싱 유즈케이스 테스트
  - `test_ingest_use_cases_upload_file.py` - 파일 업로드 유즈케이스 테스트
  - `test_ingest_use_cases_get_document_status.py` - 문서 상태 조회 유즈케이스 테스트

#### 5. Process 모듈 테스트
- **소스 코드**: `src/modules/process/`
- **테스트 파일**: 
  - `.clineignore/tests/test_process_domain_entities.py` - 도메인 엔티티 테스트
  - `test/unit/test_process_use_cases_*.py` - 유즈케이스 테스트
    - `test_process_use_cases_create_processing_job.py` - 처리 작업 생성
    - `test_process_use_cases_extract_text.py` - 텍스트 추출
    - `test_process_use_cases_create_chunks.py` - 청크 생성
    - `test_process_use_cases_generate_embeddings.py` - 임베딩 생성
    - `test_process_use_cases_deduplicate_chunks.py` - 중복 제거

#### 6. Search 모듈 테스트
- **소스 코드**: `src/modules/search/`
- **테스트 파일**: `test/unit/test_search_*.py`
  - `test_search_use_cases_search_documents.py` - 문서 검색 유즈케이스 테스트
  - `test_search_use_cases_generate_answer.py` - 답변 생성 유즈케이스 테스트
  - `test_search_infrastructure_vector_db.py` - 벡터DB 인프라 테스트

#### 7. Monitor 모듈 테스트
- **소스 코드**: `src/modules/monitor/`
- **테스트 파일**: `test/unit/test_monitor_*.py`
  - `test_monitor_domain_entities.py` - 도메인 엔티티 테스트
  - `test_monitor_application_ports.py` - 애플리케이션 포트 테스트
  - `test_monitor_application_services.py` - 애플리케이션 서비스 테스트
  - `test_monitor_use_cases_collect_metrics.py` - 메트릭 수집 유즈케이스 테스트
  - `test_monitor_infrastructure_adapters.py` - 인프라 어댑터 테스트
  - `test_monitor_infrastructure_repositories.py` - 저장소 테스트
  - `test_monitor_infrastructure_repositories_mongodb.py` - MongoDB 저장소 테스트

#### 8. API 모듈 테스트
- **소스 코드**: `src/api/`
- **테스트 파일**: `test/unit/test_api_*.py`
  - `test_api_v1_search.py` - 검색 API 테스트
  - `test_api_v1_monitor.py` - 모니터링 API 테스트

#### 9. 통합 테스트
- **테스트 파일**: `test/integration/`
  - `test_main_app.py` - 전체 애플리케이션 통합 테스트

### 테스트 실행 방법

```bash
# 특정 모듈 테스트
pytest test/unit/test_search_*.py  # 검색 모듈만
pytest test/unit/test_monitor_*.py  # 모니터링 모듈만
pytest .clineignore/tests/test_core_*.py  # 코어 모듈만

# 커버리지 포함 테스트
pytest --cov=src --cov-report=html

# 특정 테스트 클래스 실행
pytest test/unit/test_search_use_cases_search_documents.py::TestSearchDocuments
```

### 코드 품질 검사

```bash
# 코드 포맷팅
black src/ tests/
isort src/ tests/

# 타입 검사
mypy src/
```

## 라이선스

MIT License

## 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 지원

문의사항이나 이슈가 있으시면 GitHub Issues를 통해 알려주세요.
# IACSRAG_rev1
# IACSRAG_rev1
