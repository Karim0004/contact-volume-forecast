# Contact-center volume forecasting

How many contacts arrive per day and per 30 minutes over the next two weeks, and how many agents does that need?

A SARIMA model forecasts daily HPD requests two weeks ahead with a MAPE of 20.8%, against 24.7% for repeating last week, and Erlang C turns the forecast into agents per half-hour: 12 scheduled in most weekday half-hours from 9:30 to 3:30 for 31 Oct to 13 Nov 2026. The [executive summary](reports/executive_summary.md) has the one-page version.

The project follows PACE (Plan, Analyze, Construct, Execute). Decisions and findings are written up as they happened in [notes.md](notes.md).

## Plan

The forecast is for a workforce planning team that sets a two-week rota every other Monday and needs requests per day and per half-hour. Requests to New York City's housing agency (HPD) through 311 stand in for a contact center's incoming contacts.

### Data

The data is NYC Open Data's [311 Service Requests](https://data.cityofnewyork.us/d/erm2-nwe9) (dataset erm2-nwe9), filtered to agency HPD and requests created from 1 Nov 2023 to 30 Oct 2026, downloaded on 2 Nov 2026. That's 2,386,138 requests with six columns: unique_key, created_date, agency, complaint_type, borough and open_data_channel_type. 311 keeps updating old requests, so a later download may differ by a few rows.

The data is counts of requests with no personal details, so there's no ethics issue in the data itself. The staffing numbers rest on assumptions about handle time and service level, which are stated where they're used.

## Analyze

| Notebook | What it covers |
| --- | --- |
| [01_initial_exploration](notebooks/01_initial_exploration.ipynb) | Daily counts, missing days, weekday averages, channels |
| [02_aggregate](notebooks/02_aggregate.ipynb) | 30-minute and daily counts, feed gaps |
| [03_eda](notebooks/03_eda.ipynb) | Daily series, weekday, month, outliers, holidays, channels |

The HPD feed has gaps. Besides five days with no rows at all (11 to 14 Apr 2024 and 13 Jul 2024), runs of 2 hours or more with no requests add up to 155.5 hours over 29 days. Gaps are left empty instead of 0, and 36 days (the 33 with gaps and three slow-feed days in March 2024) are filled for the models but never scored.

Volume peaks in January and is lowest from May to September, and each winter is higher than the last. The biggest spikes are cold snaps, when heat complaints are 69 to 82% of requests. Six holidays run at 39 to 50% of a normal day while the other federal holidays are close to normal. Phone dropped twice, in Dec 2025 and mid-Sep 2026, with online taking up the difference, and the total doesn't show either break, so the forecast is for all channels.

## Construct

| Notebook | What it covers |
| --- | --- |
| [04_backtest](notebooks/04_backtest.ipynb) | Rolling-origin backtest harness, checked on a toy series |
| [05_baselines](notebooks/05_baselines.ipynb) | Naive, seasonal naive and a 7-day average |
| [06_models](notebooks/06_models.ipynb) | ETS, SARIMA and gradient boosting, the choice and residuals |

The backtest makes 51 forecasts, every other Monday from 4 Nov 2024 to 5 Oct 2026. Each one sees only the days before it and forecasts the next 14. MASE divides the error by the seasonal naive error on the history, so below 1 beats that benchmark.

### Results

| Model | MAPE | MASE | MAE (requests/day) |
| --- | ---: | ---: | ---: |
| Naive (yesterday) | 39.8% | 1.77 | 961 |
| Seasonal naive (same weekday last week) | 24.7% | 1.15 | 615 |
| 7-day average | 33.0% | 1.23 | 668 |
| Holt-Winters (ETS, damped trend, weekly seasonality) | 25.6% | 1.17 | 628 |
| SARIMA(1,0,1)(0,1,1)7 with a big-holiday regressor, chosen | 20.8% | 0.96 | 519 |
| Gradient boosting on 14 to 28 day lags and calendar features | 20.4% | 0.99 | 528 |

SARIMA is chosen over gradient boosting because it's better on MASE and MAE, which weigh the busy winter days more, and those decide how many agents are needed. It also gives prediction intervals directly. All models run on the log of daily requests.

## Execute

| Notebook | What it covers |
| --- | --- |
| [07_forecast](notebooks/07_forecast.ipynb) | Interval coverage and the 14-day forecast |
| [08_intraday](notebooks/08_intraday.ipynb) | Intraday profile and the forecast per half-hour |
| [09_staffing](notebooks/09_staffing.ipynb) | Erlang C agents per half-hour |

On the backtest the 80% intervals contain the actual on 82.0% of days, but only 71.3% in winter. The forecast for 31 Oct to 13 Nov 2026 is about 2,300 to 2,900 requests on weekdays and 1,600 to 2,000 at weekends.

Each day is split into half-hours with the average weekday profile from the last 52 weeks, which barely changed between the two years. Erlang C models a phone queue, so it runs on calls only: the forecast times phone's share of each half-hour over the last 6 weeks (25.1% overall). With a 5-minute handle time, 80% of calls answered within 20 seconds and 30% shrinkage, weekdays from about 9:30 to 3:30 need 12 agents scheduled in most half-hours, with a peak of 13 at 11:00 on Wednesday 11 Nov. A 4-minute or 6-minute handle time moves the two-week total by about 190 agent-hours each way.

### What didn't work

Holt-Winters never beat seasonal naive, with or without a trend. Gradient boosting with sklearn's default leaf size never learned the holiday flag, because the history only has 5 to 12 big holidays, and was 100% off on them until the leaf size came down to 5.

### Limitations and monitoring

The model has a weekly pattern but no yearly one, so it's slow to pick up the start of winter and undershoots cold snaps, and its intervals are too narrow in winter. The forecast from 31 Oct 2026 is probably low for the same reason. The handle time, service level and shrinkage are assumptions. A live version would need a weekly comparison of forecast against actual, a check of phone's share every few weeks, and a temperature forecast as the first thing to add.

## How to run

1. Python 3.11. Install the packages with `pip install -r requirements.txt`.
2. On the [dataset page](https://data.cityofnewyork.us/d/erm2-nwe9), filter to agency HPD and created dates from 1 Nov 2023 to 30 Oct 2026, keep the six columns above and export a CSV into `data/`.
3. Build the parquet file the code reads:

   ```python
   from src.data import build_parquet
   build_parquet("data/your_export.csv")
   ```

4. Run the notebooks in `notebooks/` in order, from 01 to 09. Notebook 02 saves the daily and interval tables the later ones use, and figures go to `reports/figures/`.
