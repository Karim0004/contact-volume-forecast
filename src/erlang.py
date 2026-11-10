import math


def erlang_c(traffic, agents):
    """Chance that a call has to wait, for `traffic` in Erlangs and a whole number of agents."""
    if agents <= traffic:
        return 1.0
    # A^k / k! built up one term at a time, so big numbers never overflow
    term = 1.0
    below = 1.0
    for k in range(1, agents):
        term *= traffic / k
        below += term
    top = term * traffic / agents * agents / (agents - traffic)
    return top / (below + top)


def service_level(traffic, agents, aht, target_seconds):
    """Share of calls answered within target_seconds."""
    return 1 - erlang_c(traffic, agents) * math.exp(-(agents - traffic) * target_seconds / aht)


def agents_needed(calls, aht=300, interval_seconds=1800, target_seconds=20, level=0.8):
    """Smallest number of agents that answers `level` of the calls in an interval within target_seconds.

    calls is the number of calls in the interval and aht the average handle time in seconds.
    """
    if calls <= 0:
        return 0
    traffic = calls * aht / interval_seconds
    agents = max(1, math.ceil(traffic))
    while service_level(traffic, agents, aht, target_seconds) < level:
        agents += 1
    return agents


def with_shrinkage(agents, shrinkage=0.3):
    """Agents to schedule so that `agents` are actually taking calls after breaks, training and absence."""
    return math.ceil(agents / (1 - shrinkage))
