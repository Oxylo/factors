from pathlib import Path

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