import numpy as np
import pandas as pd

from utils import (
    calculate_forward_rate_yearly,
    convert_yearly_to_monthly,
    read_workbook, run_testcase
)


fp = "/home/pieter/Insync/Gedeeld/QuantSense/Innovatie en Inspiratie/tarievengenerator/rail26.xlsx"
data = read_workbook(fp)

forward_rate_yearly = calculate_forward_rate_yearly(
    data["rts"].set_index("looptijd_jaren")["pct_rente"]
)

forward_rates_monthly = convert_yearly_to_monthly(forward_rate_yearly)


############[ input data ] ##############

age_range = np.array([34, 0])
STARTJAAR = 2026
GESLACHT_HVZ = "V"
NMAANDEN_PER_JAAR = 12
PENSIOENLEEFTIJD_MAANDEN = 12 * 68
IS_PRAENUMERANDO = False

pensioensoort = "AXN"
#########################################


nages = len(data["qy"])

df = (pd.MultiIndex.from_product(
    [["M", "F"], data["qy"]["leeftijd_jaren"], np.arange(NMAANDEN_PER_JAAR), data["qy"]["leeftijd_jaren"], np.arange(NMAANDEN_PER_JAAR)],
    names=["gender", "age0_years", "month", "projection_year_nr", "projection_month_nr"])
    .to_frame(index=False)
    .assign(index_nr=lambda x: x.projection_year_nr * NMAANDEN_PER_JAAR + x.projection_month_nr)
    .assign(calendar_year=lambda x: STARTJAAR + x["projection_year_nr"])
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
    )

# normalize tables to long format for merging
es_x_long = (data["es"]
             .loc[:, ["leeftijd_jaren", "es_hoofdvz_M", "es_hoofdvz_V"]]
             .rename(columns={"es_hoofdvz_M": "M", "es_hoofdvz_V": "F"})
             .melt(id_vars="leeftijd_jaren", var_name="gender", value_name="es_x")
             .set_index(["leeftijd_jaren", "gender"])
             )

es_y_long = (data["es"]
             .loc[:, ["leeftijd_jaren", "es_medevz_M", "es_medevz_V"]]
             .rename(columns={"es_medevz_M": "F", "es_medevz_V": "M"})
             .melt(id_vars="leeftijd_jaren", var_name="gender", value_name="es_y")
             .set_index(["leeftijd_jaren", "gender"])
             )

tab_qx_long = (data["qx"]
              .melt(id_vars="leeftijd_jaren", var_name="calendar_year", value_name="qx")
              .assign(gender="M"))

tab_qy_long = (data["qy"]
              .melt(id_vars="leeftijd_jaren", var_name="calendar_year", value_name="qx")
              .assign(gender="F"))
            
tab_q_long = (pd.concat([tab_qx_long, tab_qy_long], axis=0, ignore_index=True)
              .loc[:, ["leeftijd_jaren", "calendar_year", "gender", "qx"]]
              .set_index(["leeftijd_jaren", "calendar_year", "gender"])
              )

delta_age = (pd.DataFrame({"gender": ["M", "F"],
                            "delta_age": data["params"][["DELTA_LEEFTIJD_MAANDEN_X_MIN_Y", "DELTA_LEEFTIJD_MAANDEN_Y_MIN_X"]].values[0]})
                            .set_index("gender")
                            )

tab_hx = (data["hxy"]
          .rename(columns={"hx": "M", "hy": "F"})
          .melt(id_vars="leeftijd_jaren", var_name="gender", value_name="hx")
             .set_index(["leeftijd_jaren", "gender"])
             )

# merge all tables into one dataframe
df2 = (df.copy()
      .merge(es_x_long, how="left", left_on=["age_year_component_shifted", "gender"], right_index=True)
      .merge(tab_q_long, how="left", left_on=["age_year_component_shifted", "calendar_year_shifted", "gender"], right_index=True)
      .assign(gender_partner=lambda x: np.where(x["gender"] == "M", "F", "M"))
      .assign(qx_year=lambda x: x["qx"] * x["es_x"])
      .fillna({"qx_year": 0})
      .assign(qx_month=lambda x: 1 - (1 - x["qx_year"]) ** (1 / NMAANDEN_PER_JAAR))
      .assign(px=lambda x: 1 - x["qx_month"])
      .assign(npx=lambda x: x.groupby(["gender", "age0_years", "month"], sort=False)["px"].cumprod())
      .merge(delta_age, how="left", left_on="gender", right_index=True)
      .assign(age_y_months=lambda x: x["age_months"] - x["delta_age"])
      .drop(columns=["delta_age"], errors="ignore")
      .assign(age_y_year_component=lambda x: x["age_y_months"] // 12)
      .assign(age_y_month_component=lambda x: x["age_y_months"] % 12)
      .assign(age_y_year_component_shifted=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["age_y_year_component"].shift())
      .merge(tab_q_long, how="left", left_on=["age_y_year_component_shifted", "calendar_year_shifted", "gender_partner"], right_index=True)
      .rename(columns={"qx_x": "qx", "qx_y": "qy"}) 
      .merge(es_y_long, how="left", left_on=["age_y_year_component_shifted", "gender"], right_index=True)
      .drop(columns=["leeftijd_jaren_x", "leeftijd_jaren_y"], errors="ignore")
      .assign(qy_year=lambda x: x["qy"] * x["es_y"])
      .fillna({"qy_year": 1, "qy_month": 1})
      .assign(qy_month=lambda x: 1 - (1 - x["qy_year"]) ** (1 / NMAANDEN_PER_JAAR))
      .assign(qy_month=lambda x: np.where(x["index_nr"]==0, 0, x["qy_month"]))
      .assign(py=lambda x: 1 - x["qy_month"])
      .assign(npy=lambda x: x.groupby(["gender", "age0_years", "month"], sort=False)["py"].cumprod())
      .assign(npxy=lambda x: x["npx"] * x["npy"])
      .merge(tab_hx, how="left", left_on=["age_year_component_shifted", "gender"], right_index=True)
      .merge(tab_hx, how="left", left_on=["age_year_component_shifted_1yr", "gender"], right_index=True, suffixes=("", "_plus1yr"))
      .assign(hx_before_pd=lambda x: np.where(x["age_months_shifted"]>=PENSIOENLEEFTIJD_MAANDEN, 0, (x["hx"] + x["hx_plus1yr"])/2))
      .assign(year_index_nr=lambda x: 1 + x["index_nr"]//12)
      .assign(maturity=lambda x: x["index_nr"] + 1)
      .merge(forward_rates_monthly[["spot_rate_monthly"]], how="left", left_on="index_nr", right_index=True)
      .fillna({"spot_rate_monthly": 1})
      .assign(discount_factor=lambda x: (1 + x["spot_rate_monthly"])**(-1 * x["index_nr"]))


      )


out = run_testcase(df2, full_test=True) # , full_test=True
