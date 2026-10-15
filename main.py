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


test_data = (pd.read_excel("data/testset.xlsx", sheet_name="Sheet1")
             .assign(geslacht=lambda x: np.where(x["geslacht"]==1, "M", "F"))
             .rename(columns={"pe_leeftijd_maanden":"pe_age",
                              "leeftijd_maanden": "age0_months",
                              "geslacht": "gender",
                              "tarief_label": "insurance_type"}))


processed_data = PreProcessor(assumption_set)

# TO DO: PreProcessor
# add two methods:  apply_filter() and clear_filter()

selection = test_data[["age0_months", "gender"]].drop_duplicates()

processed_data.base["df2"] = processed_data.base["df2"].merge(selection, on=["age0_months", "gender"])
processed_data.base["df2_xy"] = processed_data.base["df2_xy"].merge(selection, on=["age0_months", "gender"])

insurance = Insurance(processed_data)

pe_ages_per_insurance_type = get_uniques_per_group(test_data[["insurance_type", "pe_age"]])

outpp = [insurance.calculate_cfs(insurance_type=k, pe_age_range=v) for k, v in pe_ages_per_insurance_type.items()]

outdf = pd.concat(outpp)

discount_factor = processed_data.forward_rates_monthly.assign(discount_factor=lambda x: (1 + x["spot_rate_monthly"])**(-1 * x.index))["discount_factor"]
                                          
result = (outdf
          .merge(discount_factor, left_on="index_nr", right_index=True, how="left")
          .fillna(1)
          .assign(discounted_cfs=lambda x: x["cfs"] * x["discount_factor"])
          .groupby(["insurance_type", "pe_age", "age0_months", "gender"])["discounted_cfs"]
          .sum())

compare = test_data.merge(result.to_frame().reset_index(), on=["pe_age", "age0_months", "gender", "insurance_type"])


errors = compare.assign(delta = lambda x: np.abs(x["factor"] - x["discounted_cfs"])).query("delta >= 0.00000001")

errors.insurance_type.value_counts()


# compare.set_index(["pe_age", "age0_months", "gender", "insurance_type"]).loc[:, 0, "F", "NPONBEPAALD"]

