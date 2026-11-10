import holidays
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

# the holidays that run at 39 to 50% of a normal day (see the EDA notes); the rest are close to normal
BIG_HOLIDAYS = {"New Year's Day", "Memorial Day", "Independence Day", "Labor Day", "Thanksgiving Day", "Christmas Day"}


def naive(history, horizon):
    """Yesterday's value for every day ahead."""
    return np.repeat(history.iloc[-1], horizon)


def seasonal_naive(history, horizon):
    """The same weekday last week."""
    return np.resize(history.iloc[-7:].to_numpy(), horizon)


def moving_average(history, horizon, window=7):
    """The average of the last `window` days for every day ahead."""
    return np.repeat(history.iloc[-window:].mean(), horizon)


def future_dates(history, horizon):
    return pd.date_range(history.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D")


def big_holiday(dates):
    us_holidays = holidays.US(years=range(dates.year.min(), dates.year.max() + 1))
    return np.array([us_holidays.get(d) in BIG_HOLIDAYS for d in dates.date], dtype=float)


def ets(history, horizon):
    """Holt-Winters on the log of the series, with a damped trend and weekly seasonality."""
    fit = ExponentialSmoothing(np.log(history), trend="add", damped_trend=True,
                               seasonal="add", seasonal_periods=7).fit()
    return np.exp(fit.forecast(horizon).to_numpy())


def sarima_forecast(history, horizon, alpha=0.2):
    """SARIMA(1,0,1)(0,1,1)7 on the log of the series, with the big holidays as a regressor.

    Returns the forecast with a lower and upper bound (an 80% interval by default), back on the request scale.
    """
    exog = big_holiday(history.index).reshape(-1, 1)
    dates = future_dates(history, horizon)
    future = big_holiday(dates).reshape(-1, 1)
    fit = SARIMAX(np.log(history), exog=exog, order=(1, 0, 1), seasonal_order=(0, 1, 1, 7)).fit(disp=False)
    pred = fit.get_forecast(horizon, exog=future)
    bounds = pred.conf_int(alpha=alpha).to_numpy()
    return pd.DataFrame({
        "forecast": np.exp(pred.predicted_mean.to_numpy()),
        "lower": np.exp(bounds[:, 0]),
        "upper": np.exp(bounds[:, 1]),
    }, index=dates)


def sarima(history, horizon):
    return sarima_forecast(history, horizon)["forecast"].to_numpy()


def lag_features(y):
    """Features that only use days at least 14 before, so every one of them is known for all 14 days ahead."""
    X = pd.DataFrame(index=y.index)
    for lag in [14, 21, 28]:
        X[f"lag_{lag}"] = y.shift(lag)
    X["mean_14_to_20"] = y.shift(14).rolling(7).mean()
    X["weekday"] = y.index.day_of_week
    X["month"] = y.index.month
    X["big_holiday"] = big_holiday(y.index)
    return X


def gradient_boosting(history, horizon, min_samples_leaf=5):
    """Gradient boosting on the log of the series, with lags of 14 days or more and calendar features.

    min_samples_leaf is 5 instead of sklearn's 20, because the history only has 5 to 12 big holidays
    and with 20 the model never splits on them.
    """
    log_y = np.log(history).reindex(history.index.append(future_dates(history, horizon)))
    X = lag_features(log_y)
    train = X.index <= history.index[-1]
    train &= X.notna().all(axis=1).to_numpy()
    model = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, min_samples_leaf=min_samples_leaf,
                                          random_state=0)
    model.fit(X[train], log_y[train])
    return np.exp(model.predict(X.iloc[-horizon:]))
