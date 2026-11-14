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

## Models, 10 Nov 2026

All three models are in src/models.py and run on the log of daily requests, so the weekly and yearly swings act as percentages. The full table is in the README and notebooks/06_models.ipynb.

1. SARIMA(1,0,1)(0,1,1)7 with a big-holiday regressor gets 20.8% MAPE and a MASE of 0.96, which is 3.9 points better than seasonal naive. Most of that is winter: 27.5% from November to March against 36.2% for seasonal naive.
2. Gradient boosting gets 20.4% MAPE and a MASE of 0.99. Its features only use days at least 14 back (lags of 14, 21 and 28 days, the mean of days 14 to 20 back, weekday, month and the big-holiday flag), so none of them is unknown for any of the 14 days ahead. The plan said lags of 1 and 7, but those aren't known for most of a 14-day forecast without forecasting step by step.
3. Holt-Winters (ETS) doesn't beat seasonal naive (25.6% against 24.7%), with or without the trend.
4. The holiday regressor is worth 1.3 points to SARIMA (22.1% without it). Its coefficient is -0.56 on the log scale, so the big holidays come out at about 57% of a normal day, close to what the EDA found.
5. Gradient boosting with sklearn's default leaf size of 20 never split on the holiday flag, because the history only has 5 to 12 big holidays, so it was 100% off on them. A leaf size of 5 fixed that (36.5% off on holidays, MAPE 21.1% down to 20.4%).

Chosen: SARIMA. Gradient boosting has a slightly lower MAPE, but SARIMA is better on MASE and MAE, which weigh the busy winter days more, and those are the days that decide how many agents are needed. It also gives prediction intervals directly, which the final forecast needs.

Residuals: the biggest misses are still cold snaps. SARIMA undershoots while a cold snap is on (40 to 65% under in late Jan 2026) and overshoots the week after it ends (up to 136% over in mid-Feb 2026), just less than seasonal naive. From April to October 73% of days are within 20%. The residual autocorrelation is under 0.1 at every lag up to 28 days, so there's no weekly pattern left that the model misses.

## Forecast, 10 Nov 2026

`sarima_forecast()` in src/models.py gives the forecast with an interval (notebooks/07_forecast.ipynb).

1. On the backtest, the 80% intervals contain the actual on 82.0% of days and the 95% ones on 92.9%, so overall they're about right. They're too narrow in winter (71.3% for the 80% interval from November to March) and a bit too wide the rest of the year (89.9%).
2. Refitted on every day up to 30 Oct 2026, the forecast for 31 Oct to 13 Nov is about 2,300 to 2,900 requests on weekdays and 1,600 to 2,000 at weekends. The forecast and both intervals are saved to data/forecast_daily.csv.
3. That's below the last two weeks of October, especially at weekends. The model has a weekly pattern but no yearly one, so it's slow to pick up the start of the heating season, the same undershoot the backtest showed at the start of winter. The real November numbers will probably land in the upper half of the intervals. A temperature forecast or a heating-season term would be the fix.

## Intraday profile, 10 Nov 2026

`intraday_profile()` and `spread_forecast()` in src/data.py (notebooks/08_intraday.ipynb).

1. The profile is each half-hour's average share of the day, by weekday, from the last 52 weeks (358 days without any feed gap). The first year's profile differs from it by only 0.1 percentage points per half-hour on average, so the shape held steady while the channel mix moved.
2. On weekdays requests climb from 7am, run at about 7 to 8% of the day per hour from 9am to 1pm and fade through the afternoon and evening. Weekends are flatter, with a lower midday peak and more of the day after 8pm. The busiest half-hours are just over 4% of the day and 3am is about 0.3%.
3. Spread over the 14-day forecast that gives 672 half-hours, saved to data/forecast_interval.csv. The busiest is 11:00 on Wednesday 11 Nov at about 122 requests.

## Erlang C staffing, 10 Nov 2026

src/erlang.py has `erlang_c()`, `service_level()`, `agents_needed()` and `with_shrinkage()` (notebooks/09_staffing.ipynb).

Assumptions: an average handle time of 5 minutes, 80% of calls answered within 20 seconds, and 30% shrinkage for breaks, training, meetings and absence.

1. Checked against the textbook case: 10 Erlangs on 11 agents gives a 0.682 chance of waiting, which `erlang_c()` matches.
2. Erlang C models a phone queue, so it runs on calls only: the forecast per half-hour times phone's share of that half-hour over the last 6 weeks (40 days, all after phone's mid-September drop). Phone is 25.1% overall, higher at night. That's where forecasting all channels pays off, since the channel shifts only have to be handled in this one share.
3. That gives about 8,435 calls over the 14 days and at most 34 in a half-hour. Weekdays from about 9:30 to 3:30 need 12 agents scheduled in most half-hours, with a peak of 13 (9 on the phones) at 11:00 on Wednesday 11 Nov. Nights never drop below 3, because one agent alone can't answer 80% within 20 seconds once there's more than a trickle of calls.
4. The handle time matters more than anything in the forecast. A 4-minute handle time needs 1,251 agent-hours on the phones over the two weeks, 5 minutes needs 1,451 and 6 minutes 1,634, so about 190 hours for every extra minute.

The weekday by half-hour table is saved to data/staffing_by_slot.csv for the dashboard.

## README and summary, 10 Nov 2026

The README now follows PACE, with the data source and download date, what each notebook covers, results, the choice, what didn't work, limitations and how to run. The one-page executive summary is in reports/. `build_parquet()` in src/data.py turns the NYC Open Data CSV export into the parquet file the rest of the code reads, and gives the same counts as before.

## Power BI page, 14 Nov 2026

powerbi/volume_forecast.pbip is a one-page report on the three files saved for it: data/forecast_daily.csv, data/backtest_results.csv and data/staffing_by_slot.csv. It's saved as a Power BI project, so the model and the report are text files in the repo. The three tables aren't related, and each visual uses one of them.

1. The cards show 33,544 forecast requests over the 14 days, the backtest MAPE for SARIMA (20.8%) and seasonal naive (24.7%), and the peak of 13 agents. The MAPE and MASE measures only count the usable days, so they match the results table.
2. The staffing file has a row per weekday and 48 half-hour columns. The query unpivots it to a row per weekday and slot, and an index column keeps the weekdays in order from Monday.
3. The backtest chart shows each forecast's 14-day total against the actual. Plotted by day it was 714 points per line and the two lines covered each other. The totals show the model reacting late to the biggest peak: the forecast from 26 Jan 2026 was 59,737 against 81,996 actual, and the next one, from 9 Feb, was 72,267 against 46,952.
4. SARIMA's error grows with the days ahead, from 10.6% on day 1 to between 18.6% and 25.2% from day 4 to day 12, then 32.8% and 33.6% on the last two days. It beats seasonal naive on 10 of the 14 days.
5. The theme draws smoothed lines by default, which bend between the points. The three line charts are set to straight lines.
