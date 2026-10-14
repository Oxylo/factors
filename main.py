import os
import numpy as np
import pandas as pd

from utils import (
      read_workbook,
      upload_df2db,
      merge_mortality_tables
)

from insurance import PreProcessor, Annuity, PartnerPension, TermInsurance
from system_settings import NMAANDEN_PER_JAAR

#
# Run test cases
#

data_dir = "/home/pieter/Insync/Gedeeld/QuantSense/Innovatie en Inspiratie/tarievengenerator/data"
fp = os.path.join(data_dir, "rail26.xlsx")
testset_fp = os.path.join(data_dir, "testset.xlsx")
data = read_workbook(fp)

dat = {"mortality_table": merge_mortality_tables(data["qx"], data["qy"]),
       "start_year": 2026,
       "delta_x_y_months": 33,  
       "delta_y_x_months": -18,
       "experience_mortality": data["es"],
       "interest_curve": data["rts"],
       "spreading_period": 1, 
       "partner_frequency": data["hxy"],
       "payout_is_praenumerando": False,   # payout_timing
       "payout_is_monthly": True}          # payout_frequency


PENSIOENLEEFTIJD_MAANDEN = 12 * 68 # pe_leeftijd_maanden

processed_data = PreProcessor(dat)

# annuities
annuity = Annuity(processed_data)

op = annuity.calculate_cfs(label="cfs_op", payments_start_age=PENSIOENLEEFTIJD_MAANDEN)
ax = annuity.calculate_cfs(label="cfs_ax")
axy = annuity.calculate_cfs(label="cfs_axy", two_lives=True)
axn = annuity.calculate_cfs(label="cfs_axn", payments_end_age=PENSIOENLEEFTIJD_MAANDEN)
ann_1 = pd.concat([op, ax, axn, axy], axis=1).copy()

# partner pension

ppension = PartnerPension(processed_data)

npbep = ppension.calculate_cfs_determined(label="cfs_npbepaald")
tnpbep = ppension.calculate_cfs_determined(label="cfs_tnpbepaald", payments_end_age=PENSIOENLEEFTIJD_MAANDEN)
nponbep = ppension.calculate_cfs_indetermined(label="cfs_pp_onbepaald", pension_age_months=PENSIOENLEEFTIJD_MAANDEN)
tnponbep = ppension.calculate_cfs_indetermined(label="cfs_tnponbepaald", pension_age_months=PENSIOENLEEFTIJD_MAANDEN, lifelong_payments=False)
partner_pension = pd.concat([npbep, tnpbep, nponbep, tnponbep], axis=1).copy()

# term insurance

tinsurance = TermInsurance(processed_data)

sg_op = tinsurance.calculate_cfs(label="cfs_sg_op", payments_start_age=PENSIOENLEEFTIJD_MAANDEN)
sg_ax = tinsurance.calculate_cfs(label="cfs_sg_ax")
sg_axn = tinsurance.calculate_cfs(label="cfs_sg_axn", payments_end_age=PENSIOENLEEFTIJD_MAANDEN)
ti = pd.concat([sg_op, sg_ax, sg_axn], axis=1).copy()


tars = (ann_1
        .merge(ti, how="left", left_index=True, right_index=True)        
        .mul(processed_data.base["df2"]["discount_factor"].to_numpy(), axis=0)
        .groupby(["gender", "age0_years", "month"])
        .sum())

tars_xy = (partner_pension
           .mul(processed_data.base["df2_xy"]["discount_factor"].to_numpy(), axis=0)
           .groupby(["gender", "age0_years", "month"])
           .sum())

# Testresultaten
tars.loc[("F", 67, 0),:] * 100
tars_xy.loc[("F", 67, 0),:] * 100


# =============================
# Overall test
# =============================

test_data = pd.read_excel("data/testset.xlsx", sheet_name="Sheet1")

age_range_annuities = test_data.query("tarief_label.isin(['OP', 'AX', 'AXN', 'AXY'])")["leeftijd_maanden"].unique().tolist()

op = annuity.calculate_cfs(label="cfs_op", payments_start_age=PENSIOENLEEFTIJD_MAANDEN, age_range=age_range_annuities)



age_range_partnerpension = test_data.query("tarief_label.isin(['NPBEPAALD', 'TNPBEPAALD', 'NPONBEPAALD', 'TNPONBEPAALD'])")["leeftijd_maanden"].unique()
age_range_terminsurance = test_data.query("tarief_label.isin(['SG_OP', 'SG_AX', 'SG_AXN'])")["leeftijd_maanden"].unique()


#### BETER IDEE DAN  DIT : ACHTERAF PAS FILTEREN OP pe_age, 

def calculate_specific_cashflow(pe_age_months: int, insurance: str, annuity: Annuity, partner_pension: PartnerPension, tinsurance: TermInsurance):

      mapper = {"OP" : {"payments_start_age": pe_age_months, "payments_end_age": None, "two_lives": False},
            "AX" : {"payments_start_age": None, "payments_end_age": None, "two_lives": False},
            "AXN" : {"payments_start_age": None, "payments_end_age": pe_age_months, "two_lives": False},
            "AXY" : {"payments_start_age": None, "payments_end_age": None, "two_lives": True},

            "NPBEPAALD" : {"payments_end_age": None, "pension_age_months": None, "lifelong_payments": True},
            "TNPBEPAALD" : {"payments_end_age": None, "pension_age_months": None, "lifelong_payments": False},
            "NPONBEPAALD" : {"payments_end_age": None, "pension_age_months": pe_age_months, "lifelong_payments": True},
            "TNPONBEPAALD" : {"payments_end_age": None, "pension_age_months": pe_age_months, "lifelong_payments": False},

            "SG_OP" : {"payments_start_age": pe_age_months, "payments_end_age": None},
            "SG_AX" : {"payments_start_age": None, "payments_end_age": None},
            "SG_AXN" : {"payments_start_age": None, "payments_end_age": pe_age_months}            
            }

      params = mapper[insurance]

      if insurance in ("OP", "AX", "AXN", "AXY"):
            return annuity.calculate_cfs(**params)
      elif insurance in ("NPONBEPAALD", "TNPONBEPAALD", "NPBEPAALD", "TNPBEPAALD"):
            return partner_pension.calculate_cfs(**params)
      elif insurance in ("SG_OP", "SG_AX", "SG_AXN"):
            return tinsurance.calculate_cfs(**params)
      else:
            return False

calculate_specific_cashflow(pe_age_months=816, insurance="OP", annuity=annuity, partner_pension=partner_pension, tinsurance=tinsurance)