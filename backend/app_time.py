"""应用业务时间。

当前产品仅面向中国大陆，数据库中的业务时间统一保存为无时区的北京时间。
这与既有 mood/chat 数据一致，并避免依赖部署主机的系统时区。
"""

from datetime import datetime, timedelta, timezone


CHINA_TIMEZONE = timezone(timedelta(hours=8))


def china_now_naive() -> datetime:
    return datetime.now(CHINA_TIMEZONE).replace(tzinfo=None)


def china_day_start_naive(now: datetime | None = None) -> datetime:
    reference = now or datetime.now(CHINA_TIMEZONE)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=CHINA_TIMEZONE)
    local_now = reference.astimezone(CHINA_TIMEZONE)
    return local_now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
