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


PENSIOENLEEFTIJD_MAANDEN = 12 * 68 # pe_leeftijd_maanden
GESLACHT_HVZ = "V"
pensioensoort = "AXN"

# settings

STARTJAAR = 2026
NMAANDEN_PER_JAAR = 12
IS_PRAENUMERANDO = False
PAYMENT_IS_MONTHLY = True
SPREIDINGSPERIODE_IN_JAREN = 1

# calculate start/end payment

startleeftijd_uitkering_maanden = PENSIOENLEEFTIJD_MAANDEN if pensioensoort in ("OP", "AXN", "WZP", "ITNP", "SG_OP", "SG_AXN") else 34 # TO DO: generalize
eindleeftijd_uitkering_maanden = PENSIOENLEEFTIJD_MAANDEN if pensioensoort in ("TNPBEPAALD", "TNPONBEPAALD") else np.inf
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
    .assign(step_function_prae=lambda x: np.minimum(x["index_nr"] // 12 + 1, SPREIDINGSPERIODE_IN_JAREN) / SPREIDINGSPERIODE_IN_JAREN)
    .assign(step_function_post=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["step_function_prae"].shift())
    .fillna({"step_function_post": 0})
    .assign(step_function = lambda x: np.where(IS_PRAENUMERANDO, x["step_function_prae"], x["step_function_post"]))
    .drop(columns=["step_function_prae", "step_function_post"])
)

out = run_testcase(df, full_test=True)

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
      .merge(tab_q_long, how="inner", left_on=["age_year_component_shifted", "calendar_year_shifted", "gender"], right_index=True)
      .assign(gender_partner=lambda x: np.where(x["gender"] == "M", "F", "M"))
      .assign(qx_year=lambda x: x["qx"] * x["es_x"])
      .fillna({"qx_year": 0})
      .assign(qx_month=lambda x: 1 - (1 - x["qx_year"]) ** (1 / NMAANDEN_PER_JAAR))
      .assign(px=lambda x: 1 - x["qx_month"])
      .assign(npx=lambda x: x.groupby(["gender", "age0_years", "month"], sort=False)["px"].cumprod())
      .assign(npx_shifted=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["npx"].shift())
      .assign(kqx = lambda x: x["npx_shifted"] * x["qx_month"])
      .fillna({"npx_shifted": 1})
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
      .assign(has_payment = lambda x: (x["age_months"] >= startleeftijd_uitkering_maanden + 1 - IS_PRAENUMERANDO) & (x["age_months"] <= eindleeftijd_uitkering_maanden))
      .assign(payment_yearly=lambda x: np.where(x["has_payment"] & (x["index_nr"] % NMAANDEN_PER_JAAR == 0), 1, 0) * np.where(NMAANDEN_PER_JAAR * x["age_year_component"] == startleeftijd_uitkering_maanden, 0.5, 1))
      .assign(payment_monthly=lambda x: np.where(x["has_payment"], 1/NMAANDEN_PER_JAAR, 0))
      .assign(payment = lambda x: PAYMENT_IS_MONTHLY * x["payment_monthly"] + (1 - PAYMENT_IS_MONTHLY) * x["payment_yearly"])
      .assign(payment_ever = lambda x: PAYMENT_IS_MONTHLY / NMAANDEN_PER_JAAR + (1 - PAYMENT_IS_MONTHLY) * (x["index_nr"] % NMAANDEN_PER_JAAR == 0))
      # calculate hx_modified
      .assign(is_year_transition=lambda x: np.where((x["age_months"] - 1) % NMAANDEN_PER_JAAR, False, True))
      .assign(is_active=lambda x: np.where(x["age_months"] <= PENSIOENLEEFTIJD_MAANDEN, True, False))
      .assign(py_is_active=lambda x: np.where(x["is_active"], x["py"], 1))
      .assign(py_is_alive_at_pensionage=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["py_is_active"].transform("prod"))
      .assign(py_shifted = lambda df:  df.groupby(["gender", "age0_years", "month"], sort=False)["py"].shift().fillna(1))
      .assign(py_year_fpa=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["py_shifted"].cumprod())
      .assign(py_year_from_pensionage=lambda x: np.where(x["is_active"], 1, x["py_year_fpa"]/x["py_is_alive_at_pensionage"]))
      .assign(py_year_from_pensionage_shifted=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["py_year_fpa"].shift(-1 * NMAANDEN_PER_JAAR).fillna(0))
      .assign(py_year_from_pensionage_shifted=lambda x: np.where(x["is_active"], 1, x["py_year_from_pensionage_shifted"]/x["py_is_alive_at_pensionage"]))
      .assign(avg=lambda x: np.where(x["is_year_transition"], (x["py_year_from_pensionage"] + x["py_year_from_pensionage_shifted"]) / 2, np.nan))
      .assign(py_avg=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["avg"].ffill())
      .assign(py_year_avg=lambda x: np.where(x["age_months"]<= PENSIOENLEEFTIJD_MAANDEN, 0, x["py_avg"]))
      .assign(hx_modified=lambda x: x["hx_before_pd"] + x["py_year_avg"]) 
      )


out = run_testcase(df2, full_test=True)




# Calculate cashflows


# CF OP

if True:
      df2 = (df2
             .assign(cfs_op = lambda x: x["npx"] *  x["payment"] * x["step_function"])
             .assign(cfs_op_discounted = lambda x: x["cfs_op"] * x["discount_factor"])
             )


# CF AX

if True:
     df2 = (df2
            .assign(cfs_ax = lambda x: x["npx"] * x["payment_ever"] * x["step_function"] * np.where((1 - PAYMENT_IS_MONTHLY) * (x["index_nr"] == 0), 0.5, 1))
            .assign(cfs_ax_discounted = lambda x: x["cfs_ax"] * x["discount_factor"] )
      )



# CF AXN // Note: requires AX and OP !

if True:
     df2 = (df2
            .assign(cfs_axn = lambda x: x["cfs_ax"] - x["cfs_op"])
            .assign(cfs_axn_discounted = lambda x: x["cfs_axn"] * x["discount_factor"])
      )


# CF AY

if True:
     df2 = (df2
            .assign(cfs_ay = lambda x: x["npy"] * x["payment_ever"] * x["step_function"] * np.where((1 - PAYMENT_IS_MONTHLY) * (x["index_nr"] == 0), 0.5, 1))
            .assign(cfs_ay_discounted = lambda x: x["cfs_ay"] * x["discount_factor"])
      )

# CF AXY

if True:
     df2 = (df2
            .assign(cfs_axy = lambda x: x["npxy"] * x["payment_ever"] * x["step_function"] * np.where((1 - PAYMENT_IS_MONTHLY) * (x["index_nr"] == 0), 0.5, 1))
            .assign(cfs_axy_discounted = lambda x: x["cfs_axy"] * x["discount_factor"])
      )


# CF NPBEPAALD

if True:
     df2 = (df2
            .assign(cfs_npbepaald = lambda x: x["cfs_ay"] - x["cfs_axy"])
            .assign(cfs_npbepaald_discounted = lambda x: x["cfs_npbepaald"] * x["discount_factor"])
      )








# CF INP


if True:
     df2 = (df2
            .assign(cfs_inp = lambda x: x["cfs_ax"])
            .assign(cfs_inp_discounted = lambda x: x["cfs_ax_discounted"])
      )


# CF NPONBEPAALD

# post = prae-numerando!

# .assign(py_avg=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["avg"].ffill())

if True:
     df2 = (df2
            .assign(payment_monthly_shifted=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["payment_monthly"].shift())
            .assign(a_cumprod_reverse=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["py"]
                    .transform(lambda s: s.iloc[::-1].cumprod().iloc[::-1].to_numpy()))
            .assign(a_cumprod_reverse_shifted=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["a_cumprod_reverse"].shift(-1).fillna(1))
            )


out = run_testcase(df2, full_test=True) # ,full_test=True



           
            # 
            # .assign(b_shifted = lambda x: x["b"].shift().fillna(0))
            # .assign(product=lambda x: x["b_shifted"] * x["c"] * x["d"] * np.sqrt(x["a"]) * x["a_cumprod_reverse_shifted"])
            # .assign(cf_unscaled=lambda x: x["product"].cumsum())
            # .assign(cf_pp_onbepaald=lambda x: x["cf_unscaled"] / x["a_cumprod_reverse_shifted"])


            
            
            #.assign(cfs_nponbepaald = lambda x: x["index_nr"])
            #.assign(cfs_nponbepaald_discounted = lambda x: x["cfs_nponbepaald"] * x["discount_factor"])
      # )







# CF NPonbep_uitg

# if True:
#      df2 = (df2
#             .assign(cfs_nponbepu = lambda x: x["index_nr"])
#             .assign(cfs_nponbepu_discounted = lambda x: x["cfs_nponbepu"] * x["discount_factor"])
#       )



# CF OP*

if True:
     df2 = (df2
            .assign(cfs_ops = lambda x: x["payment"] * x["step_function"])
            .assign(cfs_ops_discounted = lambda x: x["cfs_ops"] * x["discount_factor"])
      )


# CF AX*

if True:
     df2 = (df2
            .assign(cfs_axs = lambda x: x["payment_ever"] * x["step_function"] * np.where((1 - PAYMENT_IS_MONTHLY) * (x["index_nr"] == 0), 0.5, 1))
            .assign(cfs_axs_discounted = lambda x: x["cfs_axs"] * x["discount_factor"])
      )



# CF AXN*

if True:
     df2 = (df2
            .assign(cfs_axns = lambda x: x["cfs_axs"] - x["cfs_ops"])
            .assign(cfs_axns_discounted = lambda x: x["cfs_axns"] * x["discount_factor"])
      )


# CF SG_OP

if True:
     df2 = (df2
            .assign(cfs_sg_op = lambda x: x["payment_monthly"] * x["kqx"] * x["step_function"] * NMAANDEN_PER_JAAR)
            .assign(cfs_sg_op_discounted = lambda x: x["cfs_sg_op"] * x["discount_factor"])
      )




# CF SG_AX

if True:
     df2 = (df2
            .assign(cfs_sg_ax = lambda x: x["kqx"] * x["step_function"])
            .assign(cfs_sg_ax_discounted = lambda x: x["cfs_sg_ax"] * x["discount_factor"])
      )



# CF SG_AXN

if True:
     df2 = (df2
            .assign(cfs_sg_axn = lambda x: x["cfs_sg_ax"] - x["cfs_sg_op"])
            .assign(cfs_sg_axn_discounted = lambda x: x["cfs_sg_axn"] * x["discount_factor"])
      )




# CF ITNP


if True:
     df2 = (df2
            .assign(cfs_itnp = lambda x: x["cfs_axn"])
            .assign(cfs_itnp_discounted = lambda x: x["cfs_axn_discounted"])
      )


# CF TNPBEPAALD

if True:
     df2 = (df2
            .assign(cfs_tnpbepaald = lambda x: np.where(x["has_payment"], x["cfs_ay"] - x["cfs_axy"], 0))
            .assign(cfs_tnpbepaald_discounted = lambda x: x["cfs_tnpbepaald"] * x["discount_factor"])
      )



# CF TNPONBEPAALD


# if True:
#      df2 = (df2
#             .assign(cfs_tnponbepaald = lambda x: x["index_nr"])
#             .assign(cfs_tnponbepaald_discounted = lambda x: x["cfs_tnponbepaald"] * x["discount_factor"] * x["step_function"])
#       )

   
out = run_testcase(df2, full_test=True) # , full_test=True
