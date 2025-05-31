// MongoDB 초기화 스크립트
// 개발 환경용 데이터베이스 및 컬렉션 설정

// 데이터베이스 선택
db = db.getSiblingDB('iacsrag_dev');

// 사용자 생성
db.createUser({
  user: 'iacsrag_user',
  pwd: 'iacsrag_password',
  roles: [
    {
      role: 'readWrite',
      db: 'iacsrag_dev'
    }
  ]
});

// 컬렉션 생성 및 인덱스 설정
// Documents 컬렉션
db.createCollection('documents');
db.documents.createIndex({ "document_id": 1 }, { unique: true });
db.documents.createIndex({ "user_id": 1 });
db.documents.createIndex({ "file_type": 1 });
db.documents.createIndex({ "upload_date": 1 });
db.documents.createIndex({ "status": 1 });

// Chunks 컬렉션
db.createCollection('chunks');
db.chunks.createIndex({ "chunk_id": 1 }, { unique: true });
db.chunks.createIndex({ "document_id": 1 });
db.chunks.createIndex({ "chunk_index": 1 });
db.chunks.createIndex({ "hash": 1 });

// Users 컬렉션
db.createCollection('users');
db.users.createIndex({ "user_id": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });

// Processing Stats 컬렉션
db.createCollection('processing_stats');
db.processing_stats.createIndex({ "date": 1 });
db.processing_stats.createIndex({ "operation_type": 1 });

// Search History 컬렉션
db.createCollection('search_history');
db.search_history.createIndex({ "user_id": 1 });
db.search_history.createIndex({ "search_date": 1 });

print('MongoDB 초기화 완료: iacsrag_dev 데이터베이스 및 컬렉션 생성됨');
