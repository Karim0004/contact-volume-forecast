import numpy as np


def naive(history, horizon):
    """Yesterday's value for every day ahead."""
    return np.repeat(history.iloc[-1], horizon)


def seasonal_naive(history, horizon):
    """The same weekday last week."""
    return np.resize(history.iloc[-7:].to_numpy(), horizon)


def moving_average(history, horizon, window=7):
    """The average of the last `window` days for every day ahead."""
    return np.repeat(history.iloc[-window:].mean(), horizon)
