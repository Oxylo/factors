from pathlib import Path

import numpy as np
import pandas as pd

from system_settings import system_settings

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


def normalize(data: dict)-> dict:
    """Normalize data

    Parameters
    ----------
    data : dict
        Dictionary where each value is a pandas DataFrame.

    Returns
    -------
    dict
        Dictionary with normalized dataframes.
    """
    # normalize tables to long format for merging
    data["es_x_long"] = (data["es"]
                .loc[:, ["leeftijd_jaren", "es_hoofdvz_M", "es_hoofdvz_V"]]
                .rename(columns={"es_hoofdvz_M": "M", "es_hoofdvz_V": "F"})
                .melt(id_vars="leeftijd_jaren", var_name="gender", value_name="es_x")
                .set_index(["leeftijd_jaren", "gender"])
                )

    data["es_y_long"] = (data["es"]
                .loc[:, ["leeftijd_jaren", "es_medevz_M", "es_medevz_V"]]
                .rename(columns={"es_medevz_M": "F", "es_medevz_V": "M"})
                .melt(id_vars="leeftijd_jaren", var_name="gender", value_name="es_y")
                .set_index(["leeftijd_jaren", "gender"])
                )

    data["tab_qx_long"] = (data["qx"]
                .melt(id_vars="leeftijd_jaren", var_name="calendar_year", value_name="qx")
                .assign(gender="M"))

    data["tab_qy_long"] = (data["qy"]
                .melt(id_vars="leeftijd_jaren", var_name="calendar_year", value_name="qx")
                .assign(gender="F"))
                
    data["tab_q_long"] = (pd.concat([data["tab_qx_long"], data["tab_qy_long"]], axis=0, ignore_index=True)
                .loc[:, ["leeftijd_jaren", "calendar_year", "gender", "qx"]]
                .set_index(["leeftijd_jaren", "calendar_year", "gender"])
                )

    data["delta_age"] = (pd.DataFrame({"gender": ["M", "F"],
                                "delta_age": data["params"][["DELTA_LEEFTIJD_MAANDEN_X_MIN_Y", "DELTA_LEEFTIJD_MAANDEN_Y_MIN_X"]].values[0]})
                                .set_index("gender")
                                )

    data["tab_hx"] = (data["hxy"]
            .rename(columns={"hx": "M", "hy": "F"})
            .melt(id_vars="leeftijd_jaren", var_name="gender", value_name="hx")
                .set_index(["leeftijd_jaren", "gender"])
                )
    return data


def preprocess(data: dict, forward_rates_monthly: pd.DataFrame, settings: dict) -> dict:
    """Preprocess data for cashflow calculations.

    Parameters
    ----------
    data : dict
        Dictionary where each value is a pandas DataFrame.
    forward_rates_monthly : pd.DataFrame
        DataFrame containing monthly forward rates.
    settings : dict
        Dictionary containing parameter settings.

    Returns
    -------
    dict
        Dictionary with preprocessed dataframes.
    """
    nages = len(data["qy"])

    df = (pd.MultiIndex.from_product(
        [["M", "F"], data["qy"]["leeftijd_jaren"], np.arange(system_settings["NMAANDEN_PER_JAAR"]), data["qy"]["leeftijd_jaren"], np.arange(system_settings["NMAANDEN_PER_JAAR"])],
        names=["gender", "age0_years", "month", "projection_year_nr", "projection_month_nr"])
        .to_frame(index=False)
        .assign(index_nr=lambda x: x.projection_year_nr * system_settings["NMAANDEN_PER_JAAR"] + x.projection_month_nr)
        .assign(calendar_year=lambda x: settings["STARTJAAR"] + x["projection_year_nr"])
        .assign(age0_months=lambda x: x["age0_years"] * 12 + x["month"])
        .assign(age_months=lambda x: x["age0_months"] + x["projection_year_nr"] * 12 + x["projection_month_nr"])
        .assign(age_year_component=lambda x: x["age_months"] // 12)
        .assign(age_month_component=lambda x: x["age_months"] % 12)
        .query("age_months <= 120*12 + 11") # TO DO: make generic {12 * (nages-1)} = 121 * 12  
        # .query("filter op door gebruiker gewenste leeftijdsrange, geslacht, etc.")
        .assign(age_year_component_shifted=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["age_year_component"].shift())
        .assign(age_year_component_shifted_1yr=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["age_year_component"].shift(-11))
        .assign(calendar_year_shifted=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["calendar_year"].shift())
        .assign(age_months_shifted=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["age_months"].shift())
        .assign(step_function_prae=lambda x: np.minimum(x["index_nr"] // 12 + 1, settings["SPREIDINGSPERIODE_IN_JAREN"]) / settings["SPREIDINGSPERIODE_IN_JAREN"])
        .assign(step_function_post=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["step_function_prae"].shift())
        .fillna({"step_function_post": 0})
        .assign(step_function = lambda x: np.where(settings["IS_PRAENUMERANDO"], x["step_function_prae"], x["step_function_post"]))
        .drop(columns=["step_function_prae", "step_function_post"])
    )

    # merge all tables into one dataframe
    df2 = (df.copy()
        .merge(data["es_x_long"], how="left", left_on=["age_year_component_shifted", "gender"], right_index=True)
        .merge(data["tab_q_long"], how="inner", left_on=["age_year_component", "calendar_year", "gender"], right_index=True)
        .assign(qx=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["qx"].shift().fillna(0))
        .assign(gender_partner=lambda x: np.where(x["gender"] == "M", "F", "M"))
        .assign(qx_year=lambda x: x["qx"] * x["es_x"])
        .fillna({"qx_year": 0})
        .assign(qx_month=lambda x: 1 - (1 - x["qx_year"]) ** (1 / system_settings["NMAANDEN_PER_JAAR"]))
        .assign(px=lambda x: 1 - x["qx_month"])
        .assign(npx=lambda x: x.groupby(["gender", "age0_years", "month"], sort=False)["px"].cumprod())
        .assign(npx_shifted=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["npx"].shift())
        .assign(kqx = lambda x: x["npx_shifted"] * x["qx_month"])
        .fillna({"npx_shifted": 1})
        #.assign(has_payment = lambda x: (x["age_months"] >= startleeftijd_uitkering_maanden + 1 - IS_PRAENUMERANDO) & (x["age_months"] <= eindleeftijd_uitkering_maanden))
        #.assign(payment_yearly=lambda x: np.where(x["has_payment"] & (x["index_nr"] % NMAANDEN_PER_JAAR == 0), 1, 0) * np.where(NMAANDEN_PER_JAAR * x["age_year_component"] == startleeftijd_uitkering_maanden, 0.5, 1))
        # .assign(payment_monthly=lambda x: np.where(x["has_payment"], 1/NMAANDEN_PER_JAAR, 0))
        #.assign(payment = lambda x: PAYMENT_IS_MONTHLY * x["payment_monthly"] + (1 - PAYMENT_IS_MONTHLY) * x["payment_yearly"])
        .assign(payment_ever = lambda x: settings["PAYMENT_IS_MONTHLY"] / system_settings["NMAANDEN_PER_JAAR"] + (1 - settings["PAYMENT_IS_MONTHLY"]) * (x["index_nr"] % system_settings["NMAANDEN_PER_JAAR"] == 0))
        .merge(forward_rates_monthly[["spot_rate_monthly"]], how="left", left_on="index_nr", right_index=True)
        .fillna({"spot_rate_monthly": 1})
        .assign(discount_factor=lambda x: (1 + x["spot_rate_monthly"])**(-1 * x["index_nr"]))
        )


    df2_xy = (df2.copy()
        .merge(data["delta_age"], how="left", left_on="gender", right_index=True)
        .assign(age_y_months=lambda x: np.maximum(0, x["age_months"] - x["delta_age"]))
        .drop(columns=["delta_age"], errors="ignore")
        .assign(age_y_year_component=lambda x: x["age_y_months"] // 12)
        .assign(age_y_month_component=lambda x: x["age_y_months"] % 12)
        .assign(age_y_year_component_shifted=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["age_y_year_component"].shift())
        .merge(data["tab_q_long"], how="inner", left_on=["age_y_year_component", "calendar_year", "gender_partner"], right_index=True)
        .rename(columns={"qx_x": "qx", "qx_y": "qy"}) 
        .assign(qy=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["qy"].shift().fillna(0))      
        .merge(data["es_y_long"], how="left", left_on=["age_y_year_component_shifted", "gender"], right_index=True)
        .drop(columns=["leeftijd_jaren_x", "leeftijd_jaren_y"], errors="ignore")
        .assign(qy_year=lambda x: x["qy"] * x["es_y"])
        .fillna({"qy_year": 0}) # , "qy_month": 1
        .assign(qy_month=lambda x: 1 - (1 - x["qy_year"]) ** (1 / system_settings["NMAANDEN_PER_JAAR"]))
        .assign(qy_month=lambda x: np.where(x["index_nr"]==0, 0, x["qy_month"]))
        .assign(py=lambda x: 1 - x["qy_month"])
        .assign(npy=lambda x: x.groupby(["gender", "age0_years", "month"], sort=False)["py"].cumprod())
        .assign(npxy=lambda x: x["npx"] * x["npy"])
        .merge(data["tab_hx"], how="left", left_on=["age_year_component_shifted", "gender"], right_index=True)
        .merge(data["tab_hx"], how="left", left_on=["age_year_component_shifted_1yr", "gender"], right_index=True, suffixes=("", "_plus1yr"))
        .assign(year_index_nr=lambda x: 1 + x["index_nr"]//12)
    )

    return {"df2": df2, "df2_xy": df2_xy}
