# Notes

## Initial exploration, 2 Nov 2026

2,386,138 HPD requests from NYC 311, created between 1 Nov 2023 and 30 Oct 2026. 6 columns, no missing values, and unique_key is unique.

1. Five days have no rows at all: 11 to 14 Apr 2024 and 13 Jul 2024. The day after the April gap (15 Apr 2024) has 7,398 requests, one of the highest in the data, so it looks like a feed outage and then a backlog. These days need handling before any model sees them.
2. Volume is very seasonal. January 2026 had 129,816 requests, while the summers of 2024 and 2025 ran at about 40,000 to 47,000 a month (summer 2026 sits higher, at about 47,000 to 56,000). That fits HEAT/HOT WATER being the biggest complaint type, with 38% of all requests.
3. A day averages 2,189 requests (median 1,937), from 473 on 4 Jul 2025 to 8,228 on 8 Feb 2026. Weekdays average between 2,186 (Fri) and 2,626 (Mon), and weekends about 1,540 to 1,590.
4. Phone and online are almost level overall (47% and 46%, mobile 7%), but phone fell by a third from Nov to Dec 2025 (50,340 to 33,509) while online more than doubled. Phone stayed flat over the same months in 2024 (45,918 to 44,506), so the drop isn't seasonal.
5. A couple of small data issues: one row has complaint_type "Safety" next to the usual SAFETY, and 3 rows have borough "Unspecified".

Still to decide: forecast all channels or phone only. Point 4 matters for that, since a phone-only series has a level shift in Dec 2025.

## Aggregate, 4 Nov 2026

`interval_counts()` and `daily_counts()` in src/data.py build two tables, saved as data/interval.parquet (52,560 half-hours) and data/daily.parquet (1,095 days, 1 Nov 2023 to 30 Oct 2026). Both have total, phone, online and mobile counts, so the all-channels or phone-only question can still go either way. The daily table also has weekday, month, a US federal holiday flag from the holidays package (35 dates in the range), the hours lost to feed gaps and an outage flag.

1. The feed has more gaps than the five missing days. A run of 2 hours or more with no requests is treated as a gap, since even at 3 to 4am there are about 10 requests per half-hour on average. Besides the 5 missing days, that finds 155.5 hours of gaps spread over 29 days.
2. Gaps are left empty instead of 0. The plan was to fill missing days with zeros, but every real day in this data has requests (the quietest has 473), so a 0 would only ever stand for an outage.
3. Daily totals on those 29 days are too low, and some are among the quietest days in the data (16 Mar 2025 has 601 requests with 8.5 hours missing). Others come back with a backlog after the gap, like 15 Apr 2024 (7,398) and 18 Jan 2024 (6,054). The EDA outlier step needs to decide whether these count as missing days or get a flag in the models.
4. 518 empty half-hours in shorter runs are left as 0, and 92% of them are between midnight and 6am, so they look like real quiet spells.

## EDA, 6 Nov 2026

The charts are in notebooks/03_eda.ipynb and reports/figures.

1. Seasonality is the biggest pattern. January averages 3,019 to 4,188 requests a day depending on the year and May to September about 1,300 to 1,800, and each winter is higher than the one before.
2. Weekdays are busier than weekends. The median falls from 2,257 on Monday to 1,888 on Friday, and weekend medians are about 40% lower than weekday ones.
3. The biggest spikes are cold snaps, with HEAT/HOT WATER at 69 to 82% of requests against a January median of 58%. The models only see the calendar, so they can't see these coming, which is worth saying in the README.
4. Six holidays (Independence Day, New Year's Day, Labor Day, Thanksgiving, Christmas and Memorial Day) run at 39 to 50% of a normal day, while the other federal holidays are close to normal. The models get a flag for those six instead of one holiday flag.
5. Phone dropped twice, in early Dec 2025 and mid-Sep 2026, with online taking up the difference. The total doesn't show either break.

Decisions for the models:

- Forecast all channels. That answers the question from the initial exploration, since a phone-only series would have two level shifts in its last year.
- 36 days are treated as missing: the 33 days with 2 hours or more of feed gaps, plus 16, 17 and 19 Mar 2024, which look like a slow feed and a backlog.

## Backtest harness, 7 Nov 2026

- `model_series()` in src/data.py gives the models a complete daily series. The 36 missing days are filled with the average of the same weekday a week before and a week after, and a mask says which days are real.
- `backtest(model, y, usable)` in src/backtest.py takes any function `model(history, horizon)` that returns 14 numbers. The origins are every other Monday from 4 Nov 2024 to 5 Oct 2026 (51 origins). At each one the model gets every day before it and forecasts the next 14, so each forecast is a two-week rota and the windows don't overlap.
- `score()` gives MAPE and MASE over the real days only (700 of the 714 forecast days), so the filled days are never scored. MASE is the MAE of each origin divided by the in-sample error of the seasonal naive forecast (same weekday last week) on that origin's history, averaged over the origins. Below 1 means better than seasonal naive does one step ahead.
- Checked on a toy series going up by 1 a day: the naive model should get an MAE of 7.5 and a MASE of 7.5 / 7 = 1.07, and the harness gives exactly that.

| Model | MAPE | MASE | MAE |
| --- | ---: | ---: | ---: |
| Naive (last day) | 39.8% | 1.77 | 961 |

The naive model forecasts two weeks of weekdays from a Sunday, so weekday errors are 38 to 49% and weekend errors 27 to 30%.

## Baselines, 9 Nov 2026

The three baselines are in src/models.py and the results table is in the README.

1. Seasonal naive is the best of the three, at 24.7% MAPE and a MASE of 1.15. The weekly shape is worth more than the latest level.
2. The 7-day average beats seasonal naive on 7 of the 10 weekdays but is 56 to 67% off on weekends, because it spreads the week's average evenly over all seven days.
3. Seasonal naive is 36.2% off from November to March and 16.4% for the rest of the year, probably because a cold snap in one week gets copied into the next. Winter is where the models have the most to gain.
4. All three have a MASE above 1. That's expected, since the scale is seasonal naive one day ahead on the history and these forecasts go 14 days out.

Seasonal naive is the row the models have to beat.
