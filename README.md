# Contact-center volume forecasting

How many contacts arrive per day and per 30 minutes over the next two weeks, and how many agents does that need?

## Results

Rolling-origin backtest: 51 forecasts, made every other Monday from 4 Nov 2024 to 5 Oct 2026, each for the next 14 days. Days hit by feed outages aren't scored.

| Model | MAPE | MASE | MAE (requests/day) |
| --- | ---: | ---: | ---: |
| Naive (yesterday) | 39.8% | 1.77 | 961 |
| Seasonal naive (same weekday last week) | 24.7% | 1.15 | 615 |
| 7-day average | 33.0% | 1.23 | 668 |
