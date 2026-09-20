from pathlib import Path

import numpy as np
import pandas as pd


def read_workbook(path: str | Path) -> dict[str, pd.DataFrame]:
    """Read every sheet in an Excel workbook.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the Excel workbook.

    Returns
    -------
    dict[str, pandas.DataFrame]
        A dictionary mapping each sheet name to its dataframe.
    """
    return pd.read_excel(path, sheet_name=None)


def write_workbook(
    dataframes: dict[str, pd.DataFrame], path: str | Path
) -> None:
    """Write a dictionary of dataframes to an Excel workbook.

    Parameters
    ----------
    dataframes : dict[str, pandas.DataFrame]
        Mapping of sheet names to dataframes.
    path : str or pathlib.Path
        Destination path for the Excel workbook.
    """
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, dataframe in dataframes.items():
            dataframe.to_excel(writer, sheet_name=sheet_name, index=False)


def explode(dataframe: pd.DataFrame, explode_factor: int = 12) -> pd.DataFrame:
    """Repeat each dataframe row a fixed number of times.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        Dataframe whose rows should be repeated.
    explode_factor : int
        Number of times to repeat each row. Must be positive. Defaults to 12.

    Returns
    -------
    pandas.DataFrame
        Dataframe with repeated rows and a two-level index. The first level
        contains the original index and the second level contains subindices
        from zero to ``explode_factor - 1``.
    """
    if not isinstance(explode_factor, int) or explode_factor < 1:
        raise ValueError("explode_factor must be a positive integer")

    exploded = dataframe.loc[dataframe.index.repeat(explode_factor)].copy()
    exploded.index = pd.MultiIndex.from_product(
        [dataframe.index, range(explode_factor)],
        names=["index", "subindex"],
    )
    return exploded


def calculate_forward_rate_yearly(rates: pd.Series) -> pd.Series:
    """Calculate yearly forward rates from a rate Series.

    Parameters
    ----------
    rates : pandas.Series
        Series whose index contains durations in years and whose values are
        rate percentages.

    Returns
    -------
    pandas.Series
        Yearly forward rates with the same index as ``rates``.
    """
    factors = 1 + rates
    shifted_factors = factors.shift(1).fillna(1)
    return pd.Series(
        factors ** rates.index / shifted_factors ** (rates.index - 1) - 1,
        index=rates.index,
        name="forward_rate_yearly",
    )


def convert_yearly_to_monthly(
    rates: pd.Series, explode_factor: int = 12
) -> pd.DataFrame:
    """Convert yearly forward rates to monthly forward and spot rates.

    Parameters
    ----------
    rates : pandas.Series
        Yearly forward rates indexed by year durations.
    explode_factor : int, optional
        Number of monthly periods per year. Defaults to 12.

    Returns
    -------
    pandas.DataFrame
        Monthly forward and sport rates, named 'forward_rate_monthly' and 'spot_rate_monthy.
    """
    monthly_forward_rates = (
        explode(rates, explode_factor=explode_factor)
        .reset_index()
        .assign(
            forward_rate_yearly_factor=lambda row: (1 + row["forward_rate_yearly"])
            ** (1 / explode_factor)
        )
        .assign(product=lambda row: row["forward_rate_yearly_factor"].cumprod())
        .assign(monthnr=lambda row: row.index + 1)
        .assign(spot_rate_monthly=lambda row: row["product"] ** (1 / row["monthnr"]) - 1)
        .assign(
            spot_rate_monthly_factor=lambda row: 1 + row["spot_rate_monthly"]
        )
        .assign(
                    forward_rate_monthly=lambda row: (
                        row["forward_rate_yearly_factor"] - 1
                    )
                )
        .ffill()
        .assign(maturity = lambda x: x.index + 1)
        .set_index("maturity")
        .loc[:, ["forward_rate_monthly", "spot_rate_monthly"]]
    )
    return monthly_forward_rates
    

def run_testcase(df: pd.DataFrame, full_test: bool = False) -> pd.DataFrame | pd.Series:
    """Run a test case to verify the correctness of the dataframe.

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe to test.
    """
    # Test case: age 2 years and 10 months, female
    test_case = df[(df.age0_months == 2 * 12 + 10) & (df.gender == "F")]
    result = test_case.drop("gender", axis=1)
    print("Test case result for age 2 years and 10 months, female:")
    if full_test:
        return result
    else:
        return result.sum()
