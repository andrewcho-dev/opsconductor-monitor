"""
Time and timestamp utilities.

Provides functions for timestamp manipulation, formatting, and duration calculations.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union


def now_utc() -> datetime:
    """
    Get current UTC datetime.
    
    Returns:
        Current datetime in UTC
    """
    return datetime.now(timezone.utc)


def now_iso() -> str:
    """
    Get current UTC datetime as ISO format string.
    
    Returns:
        Current datetime as ISO string
    """
    return now_utc().isoformat()


def parse_timestamp(value: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Parse a timestamp from various formats.
    
    Handles:
    - ISO format strings
    - datetime objects
    - None
    
    Args:
        value: Timestamp value to parse
    
    Returns:
        datetime object or None
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, str):
        # Try ISO format first
        try:
            # Handle 'Z' suffix
            if value.endswith('Z'):
                value = value[:-1] + '+00:00'
            return datetime.fromisoformat(value)
        except ValueError:
            pass
        
        # Try common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%d',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    
    return None


def format_timestamp(dt: Optional[datetime], format_str: str = None) -> Optional[str]:
    """
    Format a datetime to string.
    
    Args:
        dt: datetime object
        format_str: Optional format string (defaults to ISO)
    
    Returns:
        Formatted string or None
    """
    if dt is None:
        return None
    
    if format_str:
        return dt.strftime(format_str)
    
    return dt.isoformat()


def format_duration(seconds: Union[int, float, None]) -> str:
    """
    Format a duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Human-readable duration string
    """
    if seconds is None:
        return '—'
    
    if seconds < 0:
        return '—'
    
    if seconds < 1:
        return f'{int(seconds * 1000)}ms'
    
    if seconds < 60:
        return f'{seconds:.1f}s'
    
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    
    if minutes < 60:
        return f'{minutes}m {remaining_seconds}s'
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours < 24:
        return f'{hours}h {remaining_minutes}m'
    
    days = hours // 24
    remaining_hours = hours % 24
    
    return f'{days}d {remaining_hours}h'


def calculate_duration(start: Union[str, datetime, None], end: Union[str, datetime, None]) -> Optional[float]:
    """
    Calculate duration between two timestamps in seconds.
    
    Args:
        start: Start timestamp
        end: End timestamp
    
    Returns:
        Duration in seconds or None if invalid
    """
    start_dt = parse_timestamp(start)
    end_dt = parse_timestamp(end)
    
    if start_dt is None or end_dt is None:
        return None
    
    diff = (end_dt - start_dt).total_seconds()
    return diff if diff >= 0 else None


def time_ago(dt: Union[str, datetime, None]) -> str:
    """
    Get human-readable 'time ago' string.
    
    Args:
        dt: datetime to compare against now
    
    Returns:
        Human-readable string like '5 minutes ago'
    """
    if dt is None:
        return '—'
    
    parsed = parse_timestamp(dt)
    if parsed is None:
        return '—'
    
    # Make both timezone-aware or both naive for comparison
    now = datetime.now(timezone.utc) if parsed.tzinfo else datetime.now()
    if parsed.tzinfo is None and now.tzinfo:
        now = now.replace(tzinfo=None)
    
    diff = now - parsed
    seconds = diff.total_seconds()
    
    if seconds < 0:
        return 'in the future'
    
    if seconds < 60:
        return 'just now'
    
    minutes = int(seconds // 60)
    if minutes < 60:
        return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
    
    hours = minutes // 60
    if hours < 24:
        return f'{hours} hour{"s" if hours != 1 else ""} ago'
    
    days = hours // 24
    if days < 30:
        return f'{days} day{"s" if days != 1 else ""} ago'
    
    months = days // 30
    if months < 12:
        return f'{months} month{"s" if months != 1 else ""} ago'
    
    years = months // 12
    return f'{years} year{"s" if years != 1 else ""} ago'


def hours_ago(hours: int) -> datetime:
    """
    Get datetime for N hours ago.
    
    Args:
        hours: Number of hours
    
    Returns:
        datetime N hours in the past
    """
    return now_utc() - timedelta(hours=hours)


def days_ago(days: int) -> datetime:
    """
    Get datetime for N days ago.
    
    Args:
        days: Number of days
    
    Returns:
        datetime N days in the past
    """
    return now_utc() - timedelta(days=days)


def is_within_hours(dt: Union[str, datetime, None], hours: int) -> bool:
    """
    Check if a datetime is within the last N hours.
    
    Args:
        dt: datetime to check
        hours: Number of hours
    
    Returns:
        True if within the time window
    """
    parsed = parse_timestamp(dt)
    if parsed is None:
        return False
    
    cutoff = hours_ago(hours)
    
    # Handle timezone comparison
    if parsed.tzinfo is None and cutoff.tzinfo:
        cutoff = cutoff.replace(tzinfo=None)
    elif parsed.tzinfo and cutoff.tzinfo is None:
        parsed = parsed.replace(tzinfo=None)
    
    return parsed >= cutoff
