"""
핵심 설정 모듈
환경 변수 기반 설정 관리
"""

from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env.development",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application Settings
    app_name: str = Field(default="IACS RAG Platform", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # API Settings
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    # Database Settings
    mongodb_url: str = Field(alias="MONGODB_URL")
    mongodb_host: str = Field(default="localhost", alias="MONGODB_HOST")
    mongodb_port: int = Field(default=27017, alias="MONGODB_PORT")
    mongodb_database: str = Field(alias="MONGODB_DATABASE")
    mongodb_username: Optional[str] = Field(default=None, alias="MONGODB_USERNAME")
    mongodb_password: Optional[str] = Field(default=None, alias="MONGODB_PASSWORD")
    mongodb_min_pool_size: int = Field(default=10, alias="MONGODB_MIN_POOL_SIZE")
    mongodb_max_pool_size: int = Field(default=100, alias="MONGODB_MAX_POOL_SIZE")
    
    # Vector Database Settings
    qdrant_url: str = Field(alias="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_collection_name: str = Field(default="documents", alias="QDRANT_COLLECTION_NAME")
    qdrant_vector_size: int = Field(default=1536, alias="QDRANT_VECTOR_SIZE")
    
    # Kafka Settings
    kafka_bootstrap_servers: str = Field(alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_topic_document_uploaded: str = Field(alias="KAFKA_TOPIC_DOCUMENT_UPLOADED")
    kafka_topic_text_extracted: str = Field(alias="KAFKA_TOPIC_TEXT_EXTRACTED")
    kafka_topic_chunks_created: str = Field(alias="KAFKA_TOPIC_CHUNKS_CREATED")
    kafka_topic_embeddings_generated: str = Field(alias="KAFKA_TOPIC_EMBEDDINGS_GENERATED")
    kafka_consumer_group_id: str = Field(alias="KAFKA_CONSUMER_GROUP_ID")
    
    # OpenAI Settings
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    openai_chat_model: str = Field(default="gpt-3.5-turbo", alias="OPENAI_CHAT_MODEL")
    openai_max_tokens: int = Field(default=4096, alias="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, alias="OPENAI_TEMPERATURE")
    
    # File Upload Settings
    max_file_size: str = Field(default="50MB", alias="MAX_FILE_SIZE")
    allowed_file_types: str = Field(default="pdf,docx,txt", alias="ALLOWED_FILE_TYPES")
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    temp_dir: str = Field(default="./temp", alias="TEMP_DIR")
    
    # Security Settings
    secret_key: str = Field(alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Processing Settings
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    max_concurrent_processing: int = Field(default=5, alias="MAX_CONCURRENT_PROCESSING")
    batch_size: int = Field(default=100, alias="BATCH_SIZE")
    
    # Cache Settings (Optional)
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")
    cache_ttl: int = Field(default=3600, alias="CACHE_TTL")
    
    # Monitoring Settings
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")
    
    @property
    def allowed_file_types_list(self) -> List[str]:
        """허용된 파일 타입 리스트 반환"""
        return [ext.strip() for ext in self.allowed_file_types.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        """최대 파일 크기를 바이트로 변환"""
        size_str = self.max_file_size.upper()
        if size_str.endswith("MB"):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith("KB"):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith("GB"):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)


# 전역 설정 인스턴스
settings = Settings()
