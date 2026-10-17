import os
import numpy as np
import pandas as pd

from utils import (
      read_workbook,
      upload_df2db,
      merge_mortality_tables,
      get_uniques_per_group

)

from insurance import PreProcessor, Insurance
from system_settings import NMAANDEN_PER_JAAR

#
# Run test cases
#

data_dir = "/home/pieter/Insync/Gedeeld/QuantSense/Innovatie en Inspiratie/tarievengenerator/data"
fp = os.path.join(data_dir, "rail26.xlsx")
testset_fp = os.path.join(data_dir, "testset.xlsx")
data = read_workbook(fp)



# ----------------- select assumption set ----------------------------------------


assumption_set = {"mortality_table": merge_mortality_tables(data["qx"], data["qy"]),
       "start_year": 2026,
       "delta_x_y_months": 33,  
       "delta_y_x_months": -18,
       "experience_mortality": data["es"],
       "interest_curve": data["rts"],
       "spreading_period": 10, 
       "partner_frequency": data["hxy"],
       "payout_is_praenumerando": True,   # payout_timing
       "payout_is_monthly": True}         # payout_frequency

processed_data = PreProcessor(assumption_set)  
insurance = Insurance(processed_data)

# ----------------------------------------------------------------------------------



# ------------------ calculate cashflows and factors -------------------------------


# A) individual case
individual_case = {"pe_age": 816, "age0_months": 804, "insurance_type": "OP"}
cf = insurance.cfs(selection=individual_case)
fac = insurance.factors()

# B) own selection
selection = (pd.read_excel("data/testset.xlsx", sheet_name="Sheet1")
             .assign(geslacht=lambda x: np.where(x["geslacht"]==1, "M", "F"))
             .rename(columns={"pe_leeftijd_maanden":"pe_age",
                              "leeftijd_maanden": "age0_months",
                              "geslacht": "gender",
                              "tarief_label": "insurance_type"}))

cf = insurance.cfs(selection=selection)
fac = insurance.factors()
# fac.reset_index().set_index(["insurance_type", "age0_months",  "pe_age"]).loc[("OP", 804, 816)]

# C) all factors of selected insurance types
pe_ages_per_insurance_type = {"OP": [804, 816], "AXN": [253, 300, 1000], "NPONBEPAALD": [828], "TNPONBEPAALD": [828]}
cf = insurance.cfs(selection=pe_ages_per_insurance_type)
fac = insurance.factors()
# fac.reset_index().set_index(["insurance_type", "age0_months",  "pe_age"]).loc[("TNPONBEPAALD", 150, 828)]

# -------------------------------------------------------------------------------------------











#### TEST

compare = insurance.store_factors.merge(fac.reset_index(), on=["pe_age", "age0_months", "gender", "insurance_type"])
errors = compare.assign(delta = lambda x: np.abs(x["factor"] - x["discounted_cfs"])).query("delta >= 0.00000001")
errors.insurance_type.value_counts()
compare.set_index(["pe_age", "age0_months", "gender", "insurance_type"]).loc[816, 804, "F", :].round(10) * 100



testval = {"OPx": [1,2,3], "AXN": [5,6,7]}

match testval:
    case dict():
        print("This is a dict type I") if ("OP" in testval.keys()) else print("This is a dict Type II")
    case list():
        print("This is a list")
    case pd.DataFrame():
        print("This is a DataFrame!")
    case pd.Series():
        print("This is a Series!")  


print("aap\n"
       "noot\n" 
       "mies")