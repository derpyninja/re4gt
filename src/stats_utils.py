import numpy as np


def naniqr(x, p_low=25, p_high=75):
    q_high, q_low = np.nanpercentile(x, q=[p_high, p_low])
    return q_high - q_low
