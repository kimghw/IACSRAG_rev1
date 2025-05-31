"""
Text Extraction Result Data Classes

텍스트 추출 결과를 위한 데이터 클래스들
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class TextExtractionResult:
    """텍스트 추출 결과"""
    text: str
    metadata: Dict[str, Any]
    
    @property
    def page_count(self) -> int:
        """페이지 수"""
        return self.metadata.get("page_count", 0)
    
    @property
    def word_count(self) -> int:
        """단어 수"""
        return self.metadata.get("word_count", 0)
