"""
날짜/시간 처리 유틸리티

날짜와 시간 관련 함수들을 제공합니다.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union, Generator
import pytz
import calendar


def utc_now() -> datetime:
    """
    현재 UTC 시간을 반환합니다.
    
    Returns:
        datetime: UTC 시간대의 현재 시간
    """
    return datetime.now(timezone.utc)


def get_current_utc_datetime() -> datetime:
    """
    현재 UTC 시간을 반환합니다.
    
    Returns:
        datetime: UTC 시간대의 현재 시간
    """
    return datetime.now(timezone.utc)


def get_current_utc_time() -> datetime:
    """
    현재 UTC 시간을 반환합니다. (get_current_utc_datetime의 별칭)
    
    Returns:
        datetime: UTC 시간대의 현재 시간
    """
    return datetime.now(timezone.utc)


def get_current_kst_datetime() -> datetime:
    """
    현재 KST 시간을 반환합니다.
    
    Returns:
        datetime: KST 시간대의 현재 시간
    """
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst)


def format_datetime(dt: datetime, format_str: Optional[str] = None) -> str:
    """
    datetime 객체를 문자열로 포맷합니다.
    
    Args:
        dt: 포맷할 datetime 객체
        format_str: 포맷 문자열 (None인 경우 ISO 형식 사용)
        
    Returns:
        str: 포맷된 날짜/시간 문자열
    """
    if format_str is None:
        return dt.isoformat()
    return dt.strftime(format_str)


def format_datetime_iso(dt: datetime) -> str:
    """
    datetime 객체를 ISO 8601 형식으로 포맷합니다.
    
    Args:
        dt: 포맷할 datetime 객체
        
    Returns:
        str: ISO 8601 형식의 날짜/시간 문자열
    """
    return dt.isoformat()


def parse_datetime(date_str: str, format_str: Optional[str] = None) -> datetime:
    """
    문자열을 datetime 객체로 파싱합니다.
    
    Args:
        date_str: 파싱할 날짜/시간 문자열
        format_str: 파싱 포맷 (None인 경우 ISO 형식으로 시도)
        
    Returns:
        datetime: 파싱된 datetime 객체
        
    Raises:
        ValueError: 파싱에 실패한 경우
    """
    if format_str:
        return datetime.strptime(date_str, format_str)
    else:
        # ISO 형식으로 파싱 시도
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            # 일반적인 형식들로 시도
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d",
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            raise ValueError(f"날짜/시간 형식을 파싱할 수 없습니다: {date_str}")


def to_utc(dt: datetime) -> datetime:
    """
    datetime 객체를 UTC로 변환합니다.
    
    Args:
        dt: 변환할 datetime 객체
        
    Returns:
        datetime: UTC로 변환된 datetime 객체
    """
    if dt.tzinfo is None:
        # naive datetime은 UTC로 가정
        return dt.replace(tzinfo=timezone.utc)
    else:
        return dt.astimezone(timezone.utc)


def to_timezone(dt: datetime, tz: Union[str, timezone]) -> datetime:
    """
    datetime 객체를 특정 시간대로 변환합니다.
    
    Args:
        dt: 변환할 datetime 객체
        tz: 대상 시간대 (문자열 또는 timezone 객체)
        
    Returns:
        datetime: 변환된 datetime 객체
    """
    if isinstance(tz, str):
        tz = pytz.timezone(tz)
    
    if dt.tzinfo is None:
        # naive datetime은 UTC로 가정
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(tz)


def get_korean_time(dt: Optional[datetime] = None) -> datetime:
    """
    한국 시간으로 변환합니다.
    
    Args:
        dt: 변환할 datetime 객체 (None인 경우 현재 시간)
        
    Returns:
        datetime: 한국 시간대의 datetime 객체
    """
    if dt is None:
        dt = utc_now()
    
    return to_timezone(dt, 'Asia/Seoul')


def add_days(dt: datetime, days: int) -> datetime:
    """
    날짜에 일수를 더합니다.
    
    Args:
        dt: 기준 datetime 객체
        days: 더할 일수 (음수 가능)
        
    Returns:
        datetime: 계산된 datetime 객체
    """
    return dt + timedelta(days=days)


def add_hours(dt: datetime, hours: int) -> datetime:
    """
    시간에 시간을 더합니다.
    
    Args:
        dt: 기준 datetime 객체
        hours: 더할 시간 (음수 가능)
        
    Returns:
        datetime: 계산된 datetime 객체
    """
    return dt + timedelta(hours=hours)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """
    시간에 분을 더합니다.
    
    Args:
        dt: 기준 datetime 객체
        minutes: 더할 분 (음수 가능)
        
    Returns:
        datetime: 계산된 datetime 객체
    """
    return dt + timedelta(minutes=minutes)


def get_start_of_day(dt: datetime) -> datetime:
    """
    해당 날짜의 시작 시간(00:00:00)을 반환합니다.
    
    Args:
        dt: 기준 datetime 객체
        
    Returns:
        datetime: 해당 날짜의 시작 시간
    """
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_end_of_day(dt: datetime) -> datetime:
    """
    해당 날짜의 끝 시간(23:59:59.999999)을 반환합니다.
    
    Args:
        dt: 기준 datetime 객체
        
    Returns:
        datetime: 해당 날짜의 끝 시간
    """
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def days_between(start_dt: datetime, end_dt: datetime) -> int:
    """
    두 날짜 사이의 일수를 계산합니다.
    
    Args:
        start_dt: 시작 날짜
        end_dt: 끝 날짜
        
    Returns:
        int: 일수 차이
    """
    return (end_dt.date() - start_dt.date()).days


def hours_between(start_dt: datetime, end_dt: datetime) -> float:
    """
    두 시간 사이의 시간 차이를 계산합니다.
    
    Args:
        start_dt: 시작 시간
        end_dt: 끝 시간
        
    Returns:
        float: 시간 차이 (시간 단위)
    """
    delta = end_dt - start_dt
    return delta.total_seconds() / 3600


def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """
    두 datetime이 같은 날인지 확인합니다.
    
    Args:
        dt1: 첫 번째 datetime
        dt2: 두 번째 datetime
        
    Returns:
        bool: 같은 날인 경우 True
    """
    return dt1.date() == dt2.date()


def is_weekend(dt: datetime) -> bool:
    """
    주말인지 확인합니다.
    
    Args:
        dt: 확인할 datetime 객체
        
    Returns:
        bool: 주말인 경우 True (토요일: 5, 일요일: 6)
    """
    return dt.weekday() >= 5


def get_age_in_seconds(dt: datetime) -> float:
    """
    현재 시간으로부터 경과된 시간을 초 단위로 반환합니다.
    
    Args:
        dt: 기준 시간
        
    Returns:
        float: 경과된 시간 (초)
    """
    now = utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return (now - dt).total_seconds()


def format_duration(seconds: float) -> str:
    """
    초 단위 시간을 사람이 읽기 쉬운 형태로 포맷합니다.
    
    Args:
        seconds: 초 단위 시간
        
    Returns:
        str: 포맷된 시간 문자열 (예: "2시간 30분", "1일 5시간")
    """
    if seconds < 60:
        return f"{seconds:.1f}초"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}분"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}시간"
    else:
        days = seconds / 86400
        return f"{days:.1f}일"


def get_timestamp() -> int:
    """
    현재 시간의 Unix 타임스탬프를 반환합니다.
    
    Returns:
        int: Unix 타임스탬프
    """
    return int(utc_now().timestamp())


def from_timestamp(timestamp: Union[int, float]) -> datetime:
    """
    Unix 타임스탬프를 datetime 객체로 변환합니다.
    
    Args:
        timestamp: Unix 타임스탬프
        
    Returns:
        datetime: UTC 시간대의 datetime 객체
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> float:
    """
    datetime 객체를 Unix 타임스탬프로 변환합니다.
    
    Args:
        dt: 변환할 datetime 객체
        
    Returns:
        float: Unix 타임스탬프
    """
    return dt.timestamp()


def timestamp_to_datetime(timestamp: Union[int, float]) -> datetime:
    """
    Unix 타임스탬프를 datetime 객체로 변환합니다.
    
    Args:
        timestamp: Unix 타임스탬프
        
    Returns:
        datetime: UTC 시간대의 datetime 객체
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def get_date_range(start_date: datetime, end_date: datetime, interval: str) -> Generator[datetime, None, None]:
    """
    날짜 범위를 생성합니다.
    
    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
        interval: 간격 ('days', 'hours', 'minutes')
        
    Yields:
        datetime: 범위 내의 각 날짜/시간
        
    Raises:
        ValueError: 잘못된 간격인 경우
    """
    if interval == 'days':
        delta = timedelta(days=1)
    elif interval == 'hours':
        delta = timedelta(hours=1)
    elif interval == 'minutes':
        delta = timedelta(minutes=1)
    else:
        raise ValueError(f"지원하지 않는 간격입니다: {interval}")
    
    current = start_date
    while current <= end_date:
        yield current
        current += delta


def is_business_day(dt: datetime) -> bool:
    """
    영업일인지 확인합니다 (월-금).
    
    Args:
        dt: 확인할 datetime 객체
        
    Returns:
        bool: 영업일인 경우 True
    """
    return dt.weekday() < 5  # 0-4: 월-금, 5-6: 토-일


def add_business_days(dt: datetime, days: int) -> datetime:
    """
    영업일을 더합니다.
    
    Args:
        dt: 기준 datetime 객체
        days: 더할 영업일 수 (음수 가능)
        
    Returns:
        datetime: 계산된 datetime 객체
    """
    current = dt
    remaining_days = abs(days)
    direction = 1 if days >= 0 else -1
    
    while remaining_days > 0:
        current += timedelta(days=direction)
        if is_business_day(current):
            remaining_days -= 1
    
    return current


def get_timezone_offset(dt: datetime) -> float:
    """
    시간대 오프셋을 시간 단위로 반환합니다.
    
    Args:
        dt: datetime 객체
        
    Returns:
        float: UTC로부터의 오프셋 (시간)
    """
    if dt.tzinfo is None:
        return 0.0
    
    offset = dt.utcoffset()
    if offset is None:
        return 0.0
    
    return offset.total_seconds() / 3600


def convert_timezone(dt: datetime, target_tz: timezone) -> datetime:
    """
    datetime을 다른 시간대로 변환합니다.
    
    Args:
        dt: 변환할 datetime 객체
        target_tz: 대상 시간대
        
    Returns:
        datetime: 변환된 datetime 객체
    """
    if dt.tzinfo is None:
        # naive datetime은 UTC로 가정
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(target_tz)


def get_relative_time_string(dt: datetime) -> str:
    """
    상대적인 시간 문자열을 반환합니다.
    
    Args:
        dt: 기준 datetime 객체
        
    Returns:
        str: 상대 시간 문자열 (예: "2시간 전", "30분 후")
    """
    now = get_current_utc_datetime()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    diff = now - dt
    total_seconds = diff.total_seconds()
    
    if total_seconds < 0:
        # 미래 시간
        total_seconds = abs(total_seconds)
        suffix = "후"
    else:
        suffix = "전"
    
    if total_seconds < 60:
        return f"{int(total_seconds)}초 {suffix}"
    elif total_seconds < 3600:
        minutes = int(total_seconds / 60)
        return f"{minutes}분 {suffix}"
    elif total_seconds < 86400:
        hours = int(total_seconds / 3600)
        return f"{hours}시간 {suffix}"
    else:
        days = int(total_seconds / 86400)
        return f"{days}일 {suffix}"


def validate_datetime_range(start_date: datetime, end_date: datetime, max_days: Optional[int] = None) -> tuple[bool, Optional[str]]:
    """
    날짜 범위를 검증합니다.
    
    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
        max_days: 최대 허용 일수
        
    Returns:
        tuple[bool, Optional[str]]: (유효성, 오류 메시지)
    """
    if start_date > end_date:
        return False, "시작 날짜가 종료 날짜보다 늦습니다"
    
    if max_days is not None:
        diff_days = (end_date - start_date).days
        if diff_days > max_days:
            return False, f"날짜 범위가 최대 {max_days}일을 초과합니다"
    
    return True, None


def get_week_range(dt: datetime) -> tuple[datetime, datetime]:
    """
    해당 주의 시작과 끝을 반환합니다 (월요일-일요일).
    
    Args:
        dt: 기준 datetime 객체
        
    Returns:
        tuple[datetime, datetime]: (주 시작, 주 끝)
    """
    # 월요일을 주의 시작으로 설정
    days_since_monday = dt.weekday()
    week_start = dt - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    return get_start_of_day(week_start), get_end_of_day(week_end)


def get_month_range(dt: datetime) -> tuple[datetime, datetime]:
    """
    해당 월의 시작과 끝을 반환합니다.
    
    Args:
        dt: 기준 datetime 객체
        
    Returns:
        tuple[datetime, datetime]: (월 시작, 월 끝)
    """
    # 월의 첫 날
    month_start = dt.replace(day=1)
    
    # 월의 마지막 날
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    month_end = dt.replace(day=last_day)
    
    return get_start_of_day(month_start), get_end_of_day(month_end)


def calculate_duration(start_dt: datetime, end_dt: datetime, unit: str) -> float:
    """
    두 시간 사이의 기간을 계산합니다.
    
    Args:
        start_dt: 시작 시간
        end_dt: 종료 시간
        unit: 단위 ('seconds', 'minutes', 'hours', 'days')
        
    Returns:
        float: 계산된 기간
        
    Raises:
        ValueError: 잘못된 단위인 경우
    """
    diff = end_dt - start_dt
    total_seconds = diff.total_seconds()
    
    if unit == 'seconds':
        return total_seconds
    elif unit == 'minutes':
        return total_seconds / 60
    elif unit == 'hours':
        return total_seconds / 3600
    elif unit == 'days':
        return total_seconds / 86400
    else:
        raise ValueError(f"지원하지 않는 단위입니다: {unit}")


def is_datetime_in_range(check_dt: datetime, start_dt: datetime, end_dt: datetime, 
                        start_inclusive: bool = True, end_inclusive: bool = True) -> bool:
    """
    datetime이 범위 내에 있는지 확인합니다.
    
    Args:
        check_dt: 확인할 datetime
        start_dt: 범위 시작
        end_dt: 범위 끝
        start_inclusive: 시작 날짜 포함 여부
        end_inclusive: 종료 날짜 포함 여부
        
    Returns:
        bool: 범위 내에 있는 경우 True
    """
    if start_inclusive:
        start_check = check_dt >= start_dt
    else:
        start_check = check_dt > start_dt
    
    if end_inclusive:
        end_check = check_dt <= end_dt
    else:
        end_check = check_dt < end_dt
    
    return start_check and end_check
