"""
날짜/시간 유틸리티 단위 테스트
"""

import pytest
from datetime import datetime, timezone, timedelta
from freezegun import freeze_time

from src.utils.datetime import (
    get_current_utc_datetime,
    get_current_kst_datetime,
    format_datetime,
    parse_datetime,
    datetime_to_timestamp,
    timestamp_to_datetime,
    get_date_range,
    is_business_day,
    add_business_days,
    get_timezone_offset,
    convert_timezone,
    get_relative_time_string,
    validate_datetime_range,
    get_start_of_day,
    get_end_of_day,
    get_week_range,
    get_month_range,
    calculate_duration,
    is_datetime_in_range
)


class TestBasicDatetimeFunctions:
    """기본 날짜/시간 함수 테스트"""

    @freeze_time("2024-01-15 12:30:45")
    def test_get_current_utc_datetime(self):
        """현재 UTC 시간 가져오기 테스트"""
        result = get_current_utc_datetime()
        
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 45

    @freeze_time("2024-01-15 12:30:45")
    def test_get_current_kst_datetime(self):
        """현재 KST 시간 가져오기 테스트"""
        result = get_current_kst_datetime()
        
        assert isinstance(result, datetime)
        # KST는 UTC+9
        assert result.hour == 21  # 12 + 9
        assert result.minute == 30
        assert result.second == 45

    def test_format_datetime_default(self):
        """기본 날짜 포맷팅 테스트"""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        result = format_datetime(dt)
        
        assert result == "2024-01-15T12:30:45+00:00"

    def test_format_datetime_custom_format(self):
        """커스텀 포맷 날짜 포맷팅 테스트"""
        dt = datetime(2024, 1, 15, 12, 30, 45)
        result = format_datetime(dt, format_str="%Y-%m-%d %H:%M:%S")
        
        assert result == "2024-01-15 12:30:45"

    def test_format_datetime_korean_format(self):
        """한국어 포맷 테스트"""
        dt = datetime(2024, 1, 15, 12, 30, 45)
        result = format_datetime(dt, format_str="%Y년 %m월 %d일 %H시 %M분")
        
        assert result == "2024년 01월 15일 12시 30분"


class TestDatetimeParsing:
    """날짜/시간 파싱 테스트"""

    def test_parse_datetime_iso_format(self):
        """ISO 포맷 파싱 테스트"""
        dt_str = "2024-01-15T12:30:45+00:00"
        result = parse_datetime(dt_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 45
        assert result.tzinfo == timezone.utc

    def test_parse_datetime_custom_format(self):
        """커스텀 포맷 파싱 테스트"""
        dt_str = "2024-01-15 12:30:45"
        result = parse_datetime(dt_str, format_str="%Y-%m-%d %H:%M:%S")
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 45

    def test_parse_datetime_invalid_format(self):
        """잘못된 포맷 파싱 테스트"""
        with pytest.raises(ValueError):
            parse_datetime("invalid-date-string")

    def test_parse_datetime_multiple_formats(self):
        """여러 포맷 시도 테스트"""
        test_cases = [
            ("2024-01-15", "%Y-%m-%d"),
            ("2024/01/15", "%Y/%m/%d"),
            ("15-01-2024", "%d-%m-%Y"),
        ]
        
        for dt_str, expected_fmt in test_cases:
            result = parse_datetime(dt_str, format_str=expected_fmt)
            assert result.year == 2024
            assert result.month == 1
            assert result.day == 15


class TestTimestampConversion:
    """타임스탬프 변환 테스트"""

    def test_datetime_to_timestamp(self):
        """datetime을 타임스탬프로 변환 테스트"""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        result = datetime_to_timestamp(dt)
        
        assert isinstance(result, float)
        assert result > 0

    def test_timestamp_to_datetime(self):
        """타임스탬프를 datetime으로 변환 테스트"""
        timestamp = 1705320645.0  # 2024-01-15 12:30:45 UTC
        result = timestamp_to_datetime(timestamp)
        
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_timestamp_roundtrip(self):
        """타임스탬프 변환 왕복 테스트"""
        original_dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        
        # datetime -> timestamp -> datetime
        timestamp = datetime_to_timestamp(original_dt)
        converted_dt = timestamp_to_datetime(timestamp)
        
        assert original_dt == converted_dt


class TestDateRange:
    """날짜 범위 테스트"""

    def test_get_date_range_days(self):
        """일 단위 날짜 범위 테스트"""
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 18)
        
        result = get_date_range(start_date, end_date, 'days')
        dates = list(result)
        
        assert len(dates) == 4  # 15, 16, 17, 18
        assert dates[0].day == 15
        assert dates[-1].day == 18

    def test_get_date_range_hours(self):
        """시간 단위 날짜 범위 테스트"""
        start_date = datetime(2024, 1, 15, 10)
        end_date = datetime(2024, 1, 15, 13)
        
        result = get_date_range(start_date, end_date, 'hours')
        dates = list(result)
        
        assert len(dates) == 4  # 10, 11, 12, 13
        assert dates[0].hour == 10
        assert dates[-1].hour == 13

    def test_get_date_range_invalid_interval(self):
        """잘못된 간격 테스트"""
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 18)
        
        with pytest.raises(ValueError):
            list(get_date_range(start_date, end_date, 'invalid'))


class TestBusinessDays:
    """영업일 테스트"""

    def test_is_business_day_weekday(self):
        """평일 영업일 테스트"""
        # 2024-01-15는 월요일
        monday = datetime(2024, 1, 15)
        assert is_business_day(monday) is True
        
        # 2024-01-16은 화요일
        tuesday = datetime(2024, 1, 16)
        assert is_business_day(tuesday) is True

    def test_is_business_day_weekend(self):
        """주말 영업일 테스트"""
        # 2024-01-13은 토요일
        saturday = datetime(2024, 1, 13)
        assert is_business_day(saturday) is False
        
        # 2024-01-14는 일요일
        sunday = datetime(2024, 1, 14)
        assert is_business_day(sunday) is False

    def test_add_business_days_positive(self):
        """영업일 추가 테스트"""
        # 2024-01-15는 월요일
        start_date = datetime(2024, 1, 15)
        result = add_business_days(start_date, 5)
        
        # 5 영업일 후는 2024-01-22 (월요일)
        assert result.day == 22
        assert result.weekday() == 0  # 월요일

    def test_add_business_days_negative(self):
        """영업일 빼기 테스트"""
        # 2024-01-19는 금요일
        start_date = datetime(2024, 1, 19)
        result = add_business_days(start_date, -5)
        
        # 5 영업일 전은 2024-01-12 (금요일)
        assert result.day == 12
        assert result.weekday() == 4  # 금요일

    def test_add_business_days_zero(self):
        """영업일 0일 추가 테스트"""
        start_date = datetime(2024, 1, 15)
        result = add_business_days(start_date, 0)
        
        assert result == start_date


class TestTimezoneOperations:
    """시간대 연산 테스트"""

    def test_get_timezone_offset_utc(self):
        """UTC 시간대 오프셋 테스트"""
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        offset = get_timezone_offset(dt)
        
        assert offset == 0

    def test_get_timezone_offset_kst(self):
        """KST 시간대 오프셋 테스트"""
        kst = timezone(timedelta(hours=9))
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=kst)
        offset = get_timezone_offset(dt)
        
        assert offset == 9

    def test_convert_timezone(self):
        """시간대 변환 테스트"""
        utc_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        kst = timezone(timedelta(hours=9))
        
        result = convert_timezone(utc_dt, kst)
        
        assert result.hour == 21  # 12 + 9
        assert result.tzinfo == kst

    def test_convert_timezone_naive_datetime(self):
        """naive datetime 시간대 변환 테스트"""
        naive_dt = datetime(2024, 1, 15, 12, 0, 0)
        kst = timezone(timedelta(hours=9))
        
        # naive datetime은 UTC로 가정
        result = convert_timezone(naive_dt, kst)
        
        assert result.hour == 21
        assert result.tzinfo == kst


class TestRelativeTime:
    """상대 시간 테스트"""

    @freeze_time("2024-01-15 12:00:00")
    def test_get_relative_time_string_minutes(self):
        """분 단위 상대 시간 테스트"""
        past_time = datetime(2024, 1, 15, 11, 45, 0, tzinfo=timezone.utc)
        result = get_relative_time_string(past_time)
        
        assert "15분 전" in result

    @freeze_time("2024-01-15 12:00:00")
    def test_get_relative_time_string_hours(self):
        """시간 단위 상대 시간 테스트"""
        past_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = get_relative_time_string(past_time)
        
        assert "2시간 전" in result

    @freeze_time("2024-01-15 12:00:00")
    def test_get_relative_time_string_days(self):
        """일 단위 상대 시간 테스트"""
        past_time = datetime(2024, 1, 13, 12, 0, 0, tzinfo=timezone.utc)
        result = get_relative_time_string(past_time)
        
        assert "2일 전" in result

    @freeze_time("2024-01-15 12:00:00")
    def test_get_relative_time_string_future(self):
        """미래 시간 테스트"""
        future_time = datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        result = get_relative_time_string(future_time)
        
        assert "1시간 후" in result


class TestDatetimeValidation:
    """날짜/시간 검증 테스트"""

    def test_validate_datetime_range_valid(self):
        """유효한 날짜 범위 검증 테스트"""
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 20)
        
        is_valid, error = validate_datetime_range(start_date, end_date)
        
        assert is_valid is True
        assert error is None

    def test_validate_datetime_range_invalid_order(self):
        """잘못된 순서 날짜 범위 검증 테스트"""
        start_date = datetime(2024, 1, 20)
        end_date = datetime(2024, 1, 15)
        
        is_valid, error = validate_datetime_range(start_date, end_date)
        
        assert is_valid is False
        assert "시작 날짜가 종료 날짜보다 늦습니다" in error

    def test_validate_datetime_range_max_duration(self):
        """최대 기간 초과 검증 테스트"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        max_days = 30
        
        is_valid, error = validate_datetime_range(
            start_date, end_date, max_days=max_days
        )
        
        assert is_valid is False
        assert f"날짜 범위가 최대 {max_days}일을 초과합니다" in error


class TestDayBoundaries:
    """일 경계 테스트"""

    def test_get_start_of_day(self):
        """하루 시작 시간 테스트"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = get_start_of_day(dt)
        
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_get_end_of_day(self):
        """하루 끝 시간 테스트"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = get_end_of_day(dt)
        
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        assert result.microsecond == 999999

    def test_get_start_of_day_with_timezone(self):
        """시간대가 있는 하루 시작 시간 테스트"""
        kst = timezone(timedelta(hours=9))
        dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=kst)
        result = get_start_of_day(dt)
        
        assert result.tzinfo == kst
        assert result.hour == 0


class TestWeekAndMonthRanges:
    """주/월 범위 테스트"""

    def test_get_week_range(self):
        """주 범위 테스트"""
        # 2024-01-15는 월요일
        dt = datetime(2024, 1, 15)
        start, end = get_week_range(dt)
        
        # 주의 시작은 월요일 (2024-01-15)
        assert start.day == 15
        assert start.weekday() == 0  # 월요일
        
        # 주의 끝은 일요일 (2024-01-21)
        assert end.day == 21
        assert end.weekday() == 6  # 일요일

    def test_get_month_range(self):
        """월 범위 테스트"""
        dt = datetime(2024, 1, 15)
        start, end = get_month_range(dt)
        
        # 월의 시작은 1일
        assert start.day == 1
        assert start.month == 1
        
        # 월의 끝은 31일 (1월)
        assert end.day == 31
        assert end.month == 1

    def test_get_month_range_february(self):
        """2월 월 범위 테스트 (윤년)"""
        dt = datetime(2024, 2, 15)  # 2024는 윤년
        start, end = get_month_range(dt)
        
        assert start.day == 1
        assert start.month == 2
        assert end.day == 29  # 윤년이므로 29일
        assert end.month == 2


class TestDurationCalculation:
    """기간 계산 테스트"""

    def test_calculate_duration_seconds(self):
        """초 단위 기간 계산 테스트"""
        start = datetime(2024, 1, 15, 12, 0, 0)
        end = datetime(2024, 1, 15, 12, 0, 30)
        
        result = calculate_duration(start, end, 'seconds')
        assert result == 30

    def test_calculate_duration_minutes(self):
        """분 단위 기간 계산 테스트"""
        start = datetime(2024, 1, 15, 12, 0, 0)
        end = datetime(2024, 1, 15, 12, 30, 0)
        
        result = calculate_duration(start, end, 'minutes')
        assert result == 30

    def test_calculate_duration_hours(self):
        """시간 단위 기간 계산 테스트"""
        start = datetime(2024, 1, 15, 12, 0, 0)
        end = datetime(2024, 1, 15, 15, 0, 0)
        
        result = calculate_duration(start, end, 'hours')
        assert result == 3

    def test_calculate_duration_days(self):
        """일 단위 기간 계산 테스트"""
        start = datetime(2024, 1, 15)
        end = datetime(2024, 1, 20)
        
        result = calculate_duration(start, end, 'days')
        assert result == 5

    def test_calculate_duration_invalid_unit(self):
        """잘못된 단위 기간 계산 테스트"""
        start = datetime(2024, 1, 15)
        end = datetime(2024, 1, 20)
        
        with pytest.raises(ValueError):
            calculate_duration(start, end, 'invalid')


class TestDatetimeRangeCheck:
    """날짜/시간 범위 확인 테스트"""

    def test_is_datetime_in_range_within(self):
        """범위 내 날짜 테스트"""
        start = datetime(2024, 1, 15)
        end = datetime(2024, 1, 20)
        check_date = datetime(2024, 1, 17)
        
        result = is_datetime_in_range(check_date, start, end)
        assert result is True

    def test_is_datetime_in_range_boundary(self):
        """경계 날짜 테스트"""
        start = datetime(2024, 1, 15)
        end = datetime(2024, 1, 20)
        
        # 시작 날짜
        result = is_datetime_in_range(start, start, end)
        assert result is True
        
        # 종료 날짜
        result = is_datetime_in_range(end, start, end)
        assert result is True

    def test_is_datetime_in_range_outside(self):
        """범위 밖 날짜 테스트"""
        start = datetime(2024, 1, 15)
        end = datetime(2024, 1, 20)
        
        # 시작 전
        before = datetime(2024, 1, 10)
        result = is_datetime_in_range(before, start, end)
        assert result is False
        
        # 종료 후
        after = datetime(2024, 1, 25)
        result = is_datetime_in_range(after, start, end)
        assert result is False

    def test_is_datetime_in_range_inclusive_exclusive(self):
        """포함/배타적 범위 테스트"""
        start = datetime(2024, 1, 15)
        end = datetime(2024, 1, 20)
        
        # 시작 날짜 - 배타적
        result = is_datetime_in_range(start, start, end, start_inclusive=False)
        assert result is False
        
        # 종료 날짜 - 배타적
        result = is_datetime_in_range(end, start, end, end_inclusive=False)
        assert result is False


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_leap_year_handling(self):
        """윤년 처리 테스트"""
        # 2024는 윤년
        leap_day = datetime(2024, 2, 29)
        assert leap_day.day == 29
        
        # 2023은 평년
        with pytest.raises(ValueError):
            datetime(2023, 2, 29)

    def test_daylight_saving_time(self):
        """일광절약시간 처리 테스트"""
        # 이 테스트는 시간대 라이브러리가 있을 때 더 정확하게 구현 가능
        # 현재는 기본적인 시간대 변환만 테스트
        utc_dt = datetime(2024, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        est = timezone(timedelta(hours=-5))
        
        result = convert_timezone(utc_dt, est)
        assert result.hour == 7  # 12 - 5

    def test_year_boundary(self):
        """연도 경계 테스트"""
        # 연말에서 연초로
        end_of_year = datetime(2023, 12, 31, 23, 59, 59)
        start_of_year = datetime(2024, 1, 1, 0, 0, 0)
        
        duration = calculate_duration(end_of_year, start_of_year, 'seconds')
        assert duration == 1

    def test_microsecond_precision(self):
        """마이크로초 정밀도 테스트"""
        dt1 = datetime(2024, 1, 15, 12, 0, 0, 123456)
        dt2 = datetime(2024, 1, 15, 12, 0, 0, 123457)
        
        duration = calculate_duration(dt1, dt2, 'seconds')
        assert duration == 0.000001  # 1 마이크로초


class TestIntegration:
    """통합 테스트"""

    def test_datetime_workflow(self):
        """날짜/시간 처리 워크플로우 테스트"""
        # 1. 현재 시간 가져오기
        current_utc = get_current_utc_datetime()
        current_kst = get_current_kst_datetime()
        
        # 2. 포맷팅
        formatted = format_datetime(current_utc)
        assert isinstance(formatted, str)
        
        # 3. 파싱 (시간대 정보 확인)
        parsed = parse_datetime(formatted)
        # 시간대 정보가 없는 경우 UTC로 설정
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        assert abs((parsed - current_utc).total_seconds()) < 1
        
        # 4. 타임스탬프 변환
        timestamp = datetime_to_timestamp(current_utc)
        converted_back = timestamp_to_datetime(timestamp)
        assert abs((converted_back - current_utc).total_seconds()) < 1

    def test_business_day_calculation_workflow(self):
        """영업일 계산 워크플로우 테스트"""
        # 월요일부터 시작
        start_date = datetime(2024, 1, 15)  # 월요일
        
        # 5 영업일 추가
        end_date = add_business_days(start_date, 5)
        
        # 결과 검증
        assert is_business_day(end_date) is True
        
        # 범위 내 영업일 계산
        business_days_count = 0
        for single_date in get_date_range(start_date, end_date, 'days'):
            if is_business_day(single_date):
                business_days_count += 1
        
        assert business_days_count == 6  # 시작일 포함 6일

    def test_timezone_conversion_workflow(self):
        """시간대 변환 워크플로우 테스트"""
        # UTC 시간 생성
        utc_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        # 다양한 시간대로 변환
        kst = timezone(timedelta(hours=9))
        est = timezone(timedelta(hours=-5))
        
        kst_time = convert_timezone(utc_time, kst)
        est_time = convert_timezone(utc_time, est)
        
        # 시간 차이 확인
        assert kst_time.hour == 21  # 12 + 9
        assert est_time.hour == 7   # 12 - 5
        
        # 오프셋 확인
        assert get_timezone_offset(kst_time) == 9
        assert get_timezone_offset(est_time) == -5
