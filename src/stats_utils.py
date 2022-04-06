import numpy as np
import pandas as pd
from scipy import stats


def naniqr(x, p_low=25, p_high=75):
    q_high, q_low = np.nanpercentile(x, q=[p_high, p_low])
    return q_high - q_low


def pbsr(df, col_x, col_y):
    """
    Compute PBS R.

    https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.stats.pointbiserialr.html

    Parameters
    ----------
    df
    col_x
    col_y

    Returns
    -------

    """
    x = df[col_x]

    results_dict = {}
    for col in col_y:
        y = df[col]
        r, p = stats.pointbiserialr(x=x, y=y)

        # new_colname = "{}_{}".format(col, col_x)
        results_dict[col] = [r, p]

    return pd.DataFrame.from_dict(
        results_dict, orient="index", columns=["pbsr", "pval"]
    )
