from pathlib import Path

import holidays
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_requests(path=DATA_DIR / "HPD_requests.parquet"):
    """Load the created time and channel of every request."""
    df = pd.read_parquet(path, columns=["created_date", "open_data_channel_type"])
    return df.rename(columns={"open_data_channel_type": "channel"})


def find_gaps(interval, min_length=4):
    """Mark runs of at least min_length empty intervals in a row (2 hours by default) as feed gaps."""
    empty = interval["total"] == 0
    run = (empty != empty.shift()).cumsum()
    run_length = empty.groupby(run).transform("sum")
    return empty & (run_length >= min_length)


def interval_counts(df):
    """Requests per 30-minute interval, in total and by channel, with feed gaps left empty."""
    counts = pd.crosstab(df["created_date"].dt.floor("30min"), df["channel"])
    counts.columns = [str(c).lower() for c in counts.columns]
    counts["total"] = counts.sum(axis=1)

    start = counts.index.min().normalize()
    end = counts.index.max().normalize() + pd.Timedelta("23h30min")
    intervals = pd.date_range(start, end, freq="30min", name="interval")
    interval = counts.reindex(intervals, fill_value=0).astype(float)

    # 2 hours or more with no requests at all is the HPD feed being down, not a quiet spell (see notes.md)
    interval[find_gaps(interval)] = None
    return interval


def daily_counts(interval):
    """Requests per day from the interval counts, with the hours lost to gaps and calendar features."""
    days = interval.index.normalize()
    daily = interval.groupby(days).sum(min_count=1)
    daily.index.name = "date"

    daily["gap_hours"] = interval["total"].isna().groupby(days).sum() / 2
    daily["outage"] = daily["gap_hours"] == 24

    daily["weekday"] = daily.index.day_of_week
    daily["month"] = daily.index.month
    us_holidays = holidays.US(years=range(daily.index.year.min(), daily.index.year.max() + 1))
    daily["holiday"] = [d in us_holidays for d in daily.index.date]
    return daily
