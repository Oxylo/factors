import os
import numpy as np
import pandas as pd

from utils import (
      calculate_forward_rate_yearly,
      convert_yearly_to_monthly,
      preprocess,
      read_workbook,
      run_testcase,
      normalize,
)
from system_settings import system_settings

data_dir = "/home/pieter/Insync/Gedeeld/QuantSense/Innovatie en Inspiratie/tarievengenerator/data"
fp = os.path.join(data_dir, "rail26.xlsx")
testset_fp = os.path.join(data_dir, "testset.xlsx")
data = read_workbook(fp)
test_data= pd.read_excel(testset_fp, sheet_name="testset")

forward_rate_yearly = calculate_forward_rate_yearly(
    data["rts"].set_index("looptijd_jaren")["pct_rente"]
)

forward_rates_monthly = convert_yearly_to_monthly(forward_rate_yearly)



PENSIOENLEEFTIJD_MAANDEN = 12 * 68 # pe_leeftijd_maanden

# system settings


# assumptions
settings = {"STARTJAAR": 2026, "IS_PRAENUMERANDO": False, "PAYMENT_IS_MONTHLY": True, "SPREIDINGSPERIODE_IN_JAREN": 1}

data = normalize(data)
base = preprocess(data, forward_rates_monthly, settings)



#
# Group 1: Annuities
#

def annuity_calculation(base: dict, label: str, payments_start_age: int, payments_end_age: int, two_lives: bool, settings: dict) -> pd.Series:
      startleeftijd_uitkering_maanden = -np.inf if payments_start_age is None else (payments_start_age + 1 - settings["IS_PRAENUMERANDO"])
      eindleeftijd_uitkering_maanden = np.inf if payments_end_age is None else payments_end_age
      b = base["df2_xy"] if two_lives else base["df2"]

      return (b
             .assign(has_payment = lambda x: (x["age_months"] >= startleeftijd_uitkering_maanden) & (x["age_months"] <= eindleeftijd_uitkering_maanden))
             .assign(has_payment= lambda x: np.where(settings["IS_PRAENUMERANDO"], x["has_payment"], (x["index_nr"] > 0) * x["has_payment"]))
             .assign(payment_yearly=lambda x: np.where(x["has_payment"] & (x["index_nr"] % system_settings["NMAANDEN_PER_JAAR"] == 0), 1, 0) * np.where(system_settings["NMAANDEN_PER_JAAR"] * x["age_year_component"] == startleeftijd_uitkering_maanden, 0.5, 1))
             .assign(payment_monthly=lambda x: np.where(x["has_payment"], 1/system_settings["NMAANDEN_PER_JAAR"], 0))
             .assign(payment = lambda x: settings["PAYMENT_IS_MONTHLY"] * x["payment_monthly"] + (1 - settings["PAYMENT_IS_MONTHLY"]) * x["payment_yearly"])
             .assign(cfs = lambda x: x["npx"] * x["payment"] * x["step_function"])
             .rename(columns={"cfs": label})
             .loc[:, ["gender", "age0_years", "month", "index_nr", label]]
             .set_index(["gender", "age0_years", "month", "index_nr"])
             )

op = annuity_calculation(base, "cfs_op", payments_start_age=PENSIOENLEEFTIJD_MAANDEN, payments_end_age=None, two_lives=False, settings=settings)
ax = annuity_calculation(base, "cfs_ax", payments_start_age=None, payments_end_age=None, two_lives=False, settings=settings)
axy = annuity_calculation(base, "cfs_axy", payments_start_age=None, payments_end_age=None, two_lives=True, settings=settings)
axn = annuity_calculation(base, "cfs_axn", payments_start_age=None, payments_end_age=PENSIOENLEEFTIJD_MAANDEN, two_lives=False, settings=settings)


#
# Group 2: Partner Pension
#


# Required for CF NPBEPAALD and CF NPONBEPAALD



startleeftijd_uitkering_maanden = -np.inf
eindleeftijd_uitkering_maanden = np.inf

if True:
     df2_xy = (base["df2_xy"]
            .assign(has_payment = lambda x: (x["age_months"] >= startleeftijd_uitkering_maanden) & (x["age_months"] <= eindleeftijd_uitkering_maanden))
            .assign(has_payment= lambda x: (x["index_nr"] > 0) * x["has_payment"])   # Note: partnerpension is always postnumerando, so no payment at index_nr = 0
            .assign(payment_yearly=lambda x: np.where(x["has_payment"] & (x["index_nr"] % system_settings["NMAANDEN_PER_JAAR"] == 0), 1, 0) * np.where(system_settings["NMAANDEN_PER_JAAR"] * x["age_year_component"] == startleeftijd_uitkering_maanden, 0.5, 1))
            .assign(payment_monthly=lambda x: np.where(x["has_payment"], 1/system_settings["NMAANDEN_PER_JAAR"], 0))
            .assign(payment = lambda x: settings["PAYMENT_IS_MONTHLY"] * x["payment_monthly"] + (1 - settings["PAYMENT_IS_MONTHLY"]) * x["payment_yearly"])

            .assign(cfs_axy = lambda x: x["npxy"] * x["payment"] * x["step_function"])

            .assign(cfs_ay = lambda x: x["npy"] * x["payment_ever"] * x["step_function"] * np.where((1 - settings["PAYMENT_IS_MONTHLY"]) * (x["index_nr"] == 0), 0.5, 1))
            .assign(cfs_ay_discounted = lambda x: x["cfs_ay"] * x["discount_factor"])
      )


# CF NPBEPAALD

if True:
     df2_xy = (df2_xy
            .assign(cfs_npbepaald = lambda x: x["cfs_ay"] - x["cfs_axy"])
            .assign(cfs_npbepaald_discounted = lambda x: x["cfs_npbepaald"] * x["discount_factor"])
      )

 
# CF NPONBEPAALD AND CF NPONBEP_uitgesteld

# post = prae-numerando!

if True:
     
     df2_xy = (df2_xy
            .assign(payment_yearly=lambda x: np.where(x["index_nr"] % system_settings["NMAANDEN_PER_JAAR"] == 0, 1, 0) * np.where(system_settings["NMAANDEN_PER_JAAR"] * x["age_year_component"] == x["age0_months"], 0.5, 1))
            .assign(payment_monthly=lambda x: 1/system_settings["NMAANDEN_PER_JAAR"])
            .assign(payment = lambda x: settings["PAYMENT_IS_MONTHLY"] * x["payment_monthly"] + (1 - settings["PAYMENT_IS_MONTHLY"]) * x["payment_yearly"])   # TO DO: add jaarlijkse betaling

            # calculate hx_modified
            .assign(hx_before_pd=lambda x: np.where(x["age_months_shifted"]>=PENSIOENLEEFTIJD_MAANDEN, 0, (x["hx"] + x["hx_plus1yr"])/2))      
            .assign(is_year_transition=lambda x: np.where((x["age_months"] - 1) % system_settings["NMAANDEN_PER_JAAR"], False, True))
            .assign(is_active=lambda x: np.where(x["age_months"] <= PENSIOENLEEFTIJD_MAANDEN, True, False))
            .assign(py_is_active=lambda x: np.where(x["is_active"], x["py"], 1))
            .assign(py_is_alive_at_pensionage=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["py_is_active"].transform("prod"))
            .assign(py_shifted = lambda df:  df.groupby(["gender", "age0_years", "month"], sort=False)["py"].shift().fillna(1))
            .assign(py_year_fpa=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["py_shifted"].cumprod())
            .assign(py_year_from_pensionage=lambda x: np.where(x["is_active"], 1, x["py_year_fpa"]/x["py_is_alive_at_pensionage"]))
            .assign(py_year_from_pensionage_shifted=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["py_year_fpa"].shift(-1 * system_settings["NMAANDEN_PER_JAAR"]).fillna(0))
            .assign(py_year_from_pensionage_shifted=lambda x: np.where(x["is_active"], 1, x["py_year_from_pensionage_shifted"]/x["py_is_alive_at_pensionage"]))
            .assign(avg=lambda x: np.where(x["is_year_transition"], (x["py_year_from_pensionage"] + x["py_year_from_pensionage_shifted"]) / 2, np.nan))
            .assign(py_avg=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["avg"].ffill())
            .assign(py_year_avg=lambda x: np.where(x["age_months"]<= PENSIOENLEEFTIJD_MAANDEN, 0, x["py_avg"]))
                  .assign(hx_modified=lambda x: x["hx_before_pd"] + x["py_year_avg"]) 
                  

            .assign(a_cumprod_reverse=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["py"]
                    .transform(lambda s: s.iloc[::-1].cumprod().iloc[::-1].to_numpy()))
            .assign(a_cumprod_reverse_shifted=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["a_cumprod_reverse"].shift(-1).fillna(1))
            .assign(b_shifted=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["payment_monthly"].shift().fillna(0))
            
            # NPONBEPAALD
            .assign(product=lambda x: x["b_shifted"] * x["kqx"] * x["hx_modified"] * np.sqrt(x["py"]) * x["a_cumprod_reverse_shifted"])
            .assign(cfs_unscaled=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["product"].cumsum())
            .assign(cfs_pp_onbepaald=lambda x: x["cfs_unscaled"] / x["a_cumprod_reverse_shifted"])
            .assign(cfs_pp_onbepaald=lambda x: x["cfs_pp_onbepaald"].fillna(0))
            .assign(cfs_pp_onbepaald_discounted = lambda x: x["cfs_pp_onbepaald"] * x["discount_factor"])

            # NPONBEP_uitgesteld
            .assign(kqx_uitgesteld=lambda x:np.where((x["age_months"] <= PENSIOENLEEFTIJD_MAANDEN), 0, x["kqx"]))
            .assign(product_uitgesteld=lambda x: x["b_shifted"] * x["kqx_uitgesteld"] * x["hx_modified"] * np.sqrt(x["py"]) * x["a_cumprod_reverse_shifted"])
            .assign(cfs_unscaled_uitgesteld=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["product_uitgesteld"].cumsum())
            .assign(cfs_pp_onbepaald_uitgesteld=lambda x: x["cfs_unscaled_uitgesteld"] / x["a_cumprod_reverse_shifted"])
            .assign(cfs_pp_onbepaald_uitgesteld=lambda x: x["cfs_pp_onbepaald_uitgesteld"].fillna(0))
            .assign(cfs_pp_onbepaald_discounted_uitgesteld = lambda x: x["cfs_pp_onbepaald_uitgesteld"] * x["discount_factor"])
      
            )

# CF TNPBEPAALD

eindleeftijd_uitkering_maanden = PENSIOENLEEFTIJD_MAANDEN 

if True:
     df2_xy = (df2_xy
            .assign(has_payment = lambda x: x["age_months"] <= eindleeftijd_uitkering_maanden)
            .assign(cfs_tnpbepaald = lambda x: np.where(x["has_payment"], x["cfs_ay"] - x["cfs_axy"], 0))
            .assign(cfs_tnpbepaald = lambda x: (1 - settings["IS_PRAENUMERANDO"]) * (x["index_nr"] > 0) * x["cfs_tnpbepaald"])
            .assign(cfs_tnpbepaald_discounted = lambda x: x["cfs_tnpbepaald"] * x["discount_factor"])
      )


# CF TNPONBEPAALD 


if True:
     df2_xy = (df2_xy
            .assign(cfs_tnponbepaald = lambda x: x["cfs_pp_onbepaald"] - x["cfs_pp_onbepaald_uitgesteld"])
            #.assign(cfs_tnponbepaald = lambda x: (1 - settings["IS_PRAENUMERANDO"]) * (x["index_nr"] > 0) * x["cfs_tnponbepaald"])
            .assign(cfs_tnponbepaald_discounted = lambda x: x["cfs_tnponbepaald"] * x["discount_factor"])
      )



#
# Group 3: Term Insurance
#


# CF SG_OP

startleeftijd_uitkering_maanden = (PENSIOENLEEFTIJD_MAANDEN + 1 - settings["IS_PRAENUMERANDO"])
eindleeftijd_uitkering_maanden = np.inf

if True:
     df2 = (base["df2"]
            .assign(has_payment = lambda x: (x["age_months"] >= startleeftijd_uitkering_maanden) & (x["age_months"] <= eindleeftijd_uitkering_maanden))
            .assign(has_payment= lambda x: np.where(settings["IS_PRAENUMERANDO"], x["has_payment"], (x["index_nr"] > 0) * x["has_payment"]))
            .assign(payment_yearly=lambda x: np.where(x["has_payment"] & (x["index_nr"] % system_settings["NMAANDEN_PER_JAAR"] == 0), 1, 0) * np.where(system_settings["NMAANDEN_PER_JAAR"] * x["age_year_component"] == startleeftijd_uitkering_maanden, 0.5, 1))
            .assign(payment_monthly=lambda x: np.where(x["has_payment"], 1/system_settings["NMAANDEN_PER_JAAR"], 0))
            .assign(payment = lambda x: settings["PAYMENT_IS_MONTHLY"] * x["payment_monthly"] + (1 - settings["PAYMENT_IS_MONTHLY"]) * x["payment_yearly"])
            .assign(cfs_sg_op = lambda x: x["payment"] * x["kqx"] * x["step_function"] * system_settings["NMAANDEN_PER_JAAR"])
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


#
# Run test cases
#


ann_1 = pd.concat([op, ax, axn], axis=1).copy()
ann_2 = axy.copy()



out = run_testcase(df2, full_test=False) # , full_test=True


selected_cols = ["gender",
                 "age0_years",
                 "month",
                 "cfs_op",
                 "cfs_ax",
                 "cfs_axn",                              
                 "cfs_sg_op",
                 "cfs_sg_ax",
                 "cfs_sg_axn"
                 ]


selected_cols_xy = ["gender",
                    "age0_years",
                    "month",
                    "cfs_ay",
                    "cfs_axy",
                    "cfs_npbepaald",
                    "cfs_pp_onbepaald",
                    "cfs_pp_onbepaald_uitgesteld",
                    "cfs_tnpbepaald",
                    "cfs_tnponbepaald"
                    ]



# Alleen nog verschil bij OP*, AX*, AXN* (fout in sheet?)

tars = (df2
        .merge(ann_1, how="left", left_on=["gender", "age0_years", "month", "index_nr"], right_index=True)        
        .loc[:, selected_cols].set_index(["gender", "age0_years", "month"])
        .mul(df2["discount_factor"].to_numpy(), axis=0)
        .groupby(["gender", "age0_years", "month"])
        .sum())

# Op twee levens gaan nog niet goed

tars_xy = (df2_xy
           .loc[:, selected_cols_xy].set_index(["gender", "age0_years", "month"])
        .mul(df2_xy["discount_factor"].to_numpy(), axis=0)
        .groupby(["gender", "age0_years", "month"])
        .sum())



# df2_xy.loc[:, selected_cols_xy].set_index(["gender", "age0_years", "month"]).loc[("F", 67, 0),:].sum()
                                           

# df2_xy.set_index(["gender", "age0_years", "month"]).loc[("F", 67, 0),:].sum().to_excel("~/Desktop/temp6.xlsx")


out = run_testcase(df2_xy)


# Testresultaten:
tars.loc[("F", 67, 0),:] * 100
tars_xy.loc[("F", 67, 0),:] * 100


df2_xy.set_index(["gender", "age0_years", "month"]).loc[("F", 2, 10),["has_payment", "payment", "cfs_pp_onbepaald"]].sum()

df2_xy.set_index(["gender", "age0_years", "month"]).loc[("F", 67, 0),["cfs_pp_onbepaald", "cfs_pp_onbepaald_uitgesteld", "cfs_tnponbepaald"]]