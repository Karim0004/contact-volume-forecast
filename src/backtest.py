import numpy as np
import pandas as pd


def backtest(model, y, usable, horizon=14, first_origin="2024-11-04", step=14):
    """Rolling-origin backtest.

    At each origin the model gets every day before it and forecasts the next `horizon` days.
    `model(history, horizon)` can be any function that returns `horizon` numbers.
    The default origins are every other Monday, so each forecast covers the next two weeks of
    rota and the forecast windows don't overlap.
    """
    origins = pd.date_range(first_origin, y.index[-horizon], freq=f"{step}D")
    rows = []
    for origin in origins:
        history = y[y.index < origin]
        actual = y[origin:].iloc[:horizon]
        forecast = np.asarray(model(history, horizon), dtype=float)
        # MASE scale: in-sample error of the seasonal naive forecast (same weekday last week)
        scale = (history - history.shift(7)).abs().mean()
        rows.append(pd.DataFrame({
            "origin": origin,
            "date": actual.index,
            "step": np.arange(1, horizon + 1),
            "actual": actual.to_numpy(),
            "forecast": forecast,
            "scale": scale,
            "usable": usable.reindex(actual.index).to_numpy(),
        }))
    return pd.concat(rows, ignore_index=True)


def score(results):
    """MAPE, MASE and MAE over the usable days. MASE is worked out per origin and then averaged."""
    r = results[results["usable"]]
    abs_error = (r["actual"] - r["forecast"]).abs()
    mase = abs_error.groupby(r["origin"]).mean() / r.groupby("origin")["scale"].first()
    return pd.Series({
        "MAPE": (abs_error / r["actual"]).mean() * 100,
        "MASE": mase.mean(),
        "MAE": abs_error.mean(),
        "origins": r["origin"].nunique(),
    })
