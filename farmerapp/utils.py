from datetime import date, timedelta


def previous_day(observation_date: str) -> date:
    """Satellite results are stored under the day before the requested date."""
    return date.fromisoformat(observation_date) - timedelta(days=1)
