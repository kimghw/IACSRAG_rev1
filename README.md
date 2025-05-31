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
pytest tests/unit/

# 통합 테스트
pytest tests/integration/

# 전체 테스트
pytest
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
