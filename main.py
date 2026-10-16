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


# 
# C) Ik wil alle factoren berekenen per opgegeven verzekeringsvorm 
#


# User input 

# -------------------------------------------------------------------------------------------
assumption_set = {"mortality_table": merge_mortality_tables(data["qx"], data["qy"]),
       "start_year": 2026,
       "delta_x_y_months": 33,  
       "delta_y_x_months": -18,
       "experience_mortality": data["es"],
       "interest_curve": data["rts"],
       "spreading_period": 1, 
       "partner_frequency": data["hxy"],
       "payout_is_praenumerando": False,   # payout_timing
       "payout_is_monthly": True}          # payout_frequency

pe_ages_per_insurance_type = {"OP": [804, 816], "AXN": [253, 301]}
# -------------------------------------------------------------------------------------------

# Calculation

processed_data = PreProcessor(assumption_set)  
insurance = Insurance(processed_data)
cf = insurance.cfs(pe_ages_per_insurance_type)
fac = insurance.factors()

 


# 
# B) Ik wil een grote hoeveelheid specifieke factoren berekenen
#

# User input

# -------------------------------------------------------------------------------------------

# assumption_set        See above

test_data = (pd.read_excel("data/testset.xlsx", sheet_name="Sheet1")
             .assign(geslacht=lambda x: np.where(x["geslacht"]==1, "M", "F"))
             .rename(columns={"pe_leeftijd_maanden":"pe_age",
                              "leeftijd_maanden": "age0_months",
                              "geslacht": "gender",
                              "tarief_label": "insurance_type"}))

pe_ages_per_insurance_type = get_uniques_per_group(test_data[["insurance_type", "pe_age"]])

# -------------------------------------------------------------------------------------------

# Calculation

processed_data = PreProcessor(assumption_set)  

# TO DO: PreProcessor
# add two methods:  apply_filter() and clear_filter()

selection = test_data[["age0_months", "gender"]].drop_duplicates()

processed_data.base["df2"] = processed_data.base["df2"].merge(selection, on=["age0_months", "gender"])
processed_data.base["df2_xy"] = processed_data.base["df2_xy"].merge(selection, on=["age0_months", "gender"])

insurance = Insurance(processed_data)
cf = insurance.cfs(pe_ages_per_insurance_type)
fac = insurance.factors()





#
# A) Ik wil één specifieke factor berekenen
#

processed_data = PreProcessor(assumption_set)
insurance = Insurance(processed_data)


cf = insurance.cfs(pe_ages_per_insurance_type)
fac = insurance.factors()










#### TEST

compare = test_data.merge(fac.to_frame().reset_index(), on=["pe_age", "age0_months", "gender", "insurance_type"])
errors = compare.assign(delta = lambda x: np.abs(x["factor"] - x["discounted_cfs"])).query("delta >= 0.00000001")
errors.insurance_type.value_counts()
compare.set_index(["pe_age", "age0_months", "gender", "insurance_type"]).loc[816, 804, "F", :].round(10) * 100

