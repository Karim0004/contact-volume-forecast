from pathlib import Path

import holidays
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# 16 and 17 Mar 2024 look like a slow feed and 19 Mar 2024 like the backlog after it (see notes.md)
SLOW_FEED_DAYS = ["2024-03-16", "2024-03-17", "2024-03-19"]


def build_parquet(csv_path, out_path=DATA_DIR / "HPD_requests.parquet"):
    """Turn the NYC Open Data CSV export into the parquet file that load_requests() reads."""
    df = pd.read_csv(csv_path, parse_dates=["created_date"])
    df = df[df["agency"] == "HPD"]
    df.to_parquet(out_path, index=False)


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


def model_series(daily):
    """Daily total for the models, plus a mask of the days that are real.

    Days with 2 hours or more of feed gaps and the slow feed days are filled with the average of the
    same weekday a week before and a week after, so the models get a complete series.
    """
    usable = (daily["gap_hours"] < 2) & ~daily.index.isin(pd.to_datetime(SLOW_FEED_DAYS))
    y = daily["total"].where(usable)
    nearby = pd.concat([y.shift(7), y.shift(-7)], axis=1).mean(axis=1)
    y = y.fillna(nearby).asfreq("D")
    return y, usable


def intraday_profile(interval, days):
    """Each 30-minute slot's average share of the day's requests, by weekday (rows 0 = Monday to 6 = Sunday)."""
    total = interval.loc[interval.index.normalize().isin(days), "total"]
    share = total / total.groupby(total.index.normalize()).transform("sum")
    return share.groupby([share.index.day_of_week, share.index.time]).mean().unstack()


def spread_forecast(daily_forecast, profile):
    """Split a daily forecast into 30-minute slots using the profile for each day's weekday."""
    parts = []
    for day, total in daily_forecast.items():
        shares = profile.loc[day.day_of_week]
        slots = [pd.Timestamp.combine(day.date(), t) for t in shares.index]
        parts.append(pd.Series(total * shares.to_numpy(), index=slots))
    return pd.concat(parts).rename_axis("interval")
