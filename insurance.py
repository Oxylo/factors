import numpy as np
import pandas as pd
from utils import (convert_yearly_to_monthly,
                   calculate_forward_rate_yearly,
                   preprocess,
                   normalize)
from system_settings import NMAANDEN_PER_JAAR, DEFAULT_PENSION_AGE_MONTHS


class PreProcessor:
      """
      Holds source data and settings for the cashflow calculations and offers some data preprocessing utilities.

      Parameters:
      data (dict): A dictionary containing the following pandas Dataframes: qx, qy, es, hxy, rts plus the following settings: start_year, delta_x_y_months, delta_x_y_months, payout_is_monthly, spreading_period, payout_is_praenuemrando
      """
      def __init__(self, data: dict):
            self.data = data
            self.base = self.calculate_base()

      def normalize_data(self) -> dict:
            return normalize(self.data)

      def calculate_base(self) -> dict:
            normalized_data = self.normalize_data()
            forward_rates_monthly = convert_yearly_to_monthly(calculate_forward_rate_yearly(self.data["interest_curve"].set_index("looptijd_jaren")["pct_rente"]))
            return preprocess(normalized_data, forward_rates_monthly)


class Annuity:
      """
      Represents an annuity calculation, with methods to compute the cash flows based on the provided (processed) data.
      """
      def __init__(self, processed_data: dict):  
            self.processed_data = processed_data
            
            
      def calculate_cfs(self, label: str="ax", payments_start_age: int|None=None, payments_end_age: int|None=None, two_lives: bool=False, age_range: list|None=None) -> pd.Series:
            startleeftijd_uitkering_maanden = -np.inf if payments_start_age is None else (payments_start_age + 1 - self.processed_data.data["payout_is_praenumerando"])
            eindleeftijd_uitkering_maanden = np.inf if payments_end_age is None else payments_end_age
            if age_range:
                  b = self.processed_data.base["df2_xy"].query(f"age0_months.isin({age_range})") if two_lives else self.processed_data.base["df2"].query(f"age0_months.isin({age_range})")
            else:
                  b = self.processed_data.base["df2_xy"] if two_lives else self.processed_data.base["df2"]

            return (b
                  .assign(has_payment = lambda x: (x["age_months"] >= startleeftijd_uitkering_maanden) & (x["age_months"] <= eindleeftijd_uitkering_maanden))
                  .assign(has_payment= lambda x: np.where(self.processed_data.data["payout_is_praenumerando"], x["has_payment"], (x["index_nr"] > 0) * x["has_payment"]))
                  .assign(payment_yearly=lambda x: np.where(x["has_payment"] & (x["index_nr"] % NMAANDEN_PER_JAAR == 0), 1, 0) * np.where(NMAANDEN_PER_JAAR * x["age_year_component"] == startleeftijd_uitkering_maanden, 0.5, 1))
                  .assign(payment_monthly=lambda x: np.where(x["has_payment"], 1/NMAANDEN_PER_JAAR, 0))
                  .assign(payment = lambda x: self.processed_data.data["payout_is_monthly"] * x["payment_monthly"] + (1 - self.processed_data.data["payout_is_monthly"]) * x["payment_yearly"])
                  .assign(prob_alive = lambda x: x["npxy"] if two_lives else x["npx"])
                  .assign(cfs = lambda x: x["prob_alive"] * x["payment"] * x["step_function"])
                  .rename(columns={"cfs": label})
                  .loc[:, ["gender", "age0_years", "month", "index_nr", label]]
                  .set_index(["gender", "age0_years", "month", "index_nr"])
                  )


class PartnerPension:
      """
      Represents a partner pension calculation, with methods to compute the cash flows based on the provided (processed) data.
      """
      def __init__(self, processed_data: dict):  
            self.processed_data = processed_data
            
      def calculate_cfs_determined(self, label: str="ax|y", payments_start_age: int|None=None, payments_end_age: int|None=None, age_range: list|None=None) -> pd.Series:
            startleeftijd_uitkering_maanden = -np.inf if payments_start_age is None else (payments_start_age + 1 - self.processed_data.data["payout_is_praenumerando"])
            eindleeftijd_uitkering_maanden = np.inf if payments_end_age is None else payments_end_age
            if age_range:
                b = self.processed_data.base["df2_xy"].query(f"age0_months.isin({age_range})") 
            else:
                b = self.processed_data.base["df2_xy"] 

            return (b
                  .assign(has_payment = lambda x: (x["age_months"] >= startleeftijd_uitkering_maanden) & (x["age_months"] <= eindleeftijd_uitkering_maanden))
                  .assign(has_payment= lambda x: (x["index_nr"] > 0) * x["has_payment"])   # Note: partnerpension is always postnumerando, so no payment at index_nr = 0
                  .assign(payment_yearly=lambda x: np.where(x["has_payment"] & (x["index_nr"] % NMAANDEN_PER_JAAR == 0), 1, 0) * np.where(NMAANDEN_PER_JAAR * x["age_year_component"] == startleeftijd_uitkering_maanden, 0.5, 1))
                  .assign(payment_monthly=lambda x: np.where(x["has_payment"], 1/NMAANDEN_PER_JAAR, 0))
                  .assign(payment = lambda x: self.processed_data.data["payout_is_monthly"] * x["payment_monthly"] + (1 - self.processed_data.data["payout_is_monthly"]) * x["payment_yearly"])
                  .assign(cfs_axy = lambda x: x["npxy"] * x["payment"] * x["step_function"])
                  .assign(cfs_ay = lambda x: x["npy"] * x["payment_ever"] * x["step_function"] * np.where((1 - self.processed_data.data["payout_is_monthly"]) * (x["index_nr"] == 0), 0.5, 1))
                  .assign(cfs_ay_discounted = lambda x: x["cfs_ay"] * x["discount_factor"])
                  .assign(cfs = lambda x: np.where(x["has_payment"], x["cfs_ay"] - x["cfs_axy"], 0))
                  .assign(cfs = lambda x: (1 - self.processed_data.data["payout_is_praenumerando"]) * (x["index_nr"] > 0) * x["cfs"])  # Deze regel moet er waarschijnlijk uit, want partnerpensioen is altijd postnumerando, dus geen betaling bij index_nr = 0
                  .rename(columns={"cfs": label})
                  .loc[:, ["gender", "age0_years", "month", "index_nr", label]]
                  .set_index(["gender", "age0_years", "month", "index_nr"])
                  )

      def calculate_cfs_indetermined(self, label: str="ax|yh", pension_age_months: int=DEFAULT_PENSION_AGE_MONTHS, lifelong_payments: bool=True, age_range: list|None=None) -> pd.Series:

            if age_range:
                b = self.processed_data.base["df2_xy"].query(f"age0_months.isin({age_range})") 
            else:
                b = self.processed_data.base["df2_xy"] 

            b =  (b
                  .assign(payment_yearly=lambda x: np.where(x["index_nr"] % NMAANDEN_PER_JAAR == 0, 1, 0) * np.where(NMAANDEN_PER_JAAR * x["age_year_component"] == x["age0_months"], 0.5, 1))
                  .assign(payment_monthly=lambda x: 1/NMAANDEN_PER_JAAR)
                  .assign(payment = lambda x: self.processed_data.data["payout_is_monthly"] * x["payment_monthly"] + (1 - self.processed_data.data["payout_is_monthly"]) * x["payment_yearly"])   

                  # hx_modified
                  .assign(hx_before_pd=lambda x: np.where(x["age_months_shifted"]>=pension_age_months, 0, (x["hx"] + x["hx_plus1yr"])/2))      
                  .assign(is_year_transition=lambda x: np.where((x["age_months"] - 1) % NMAANDEN_PER_JAAR, False, True))
                  .assign(is_active=lambda x: np.where(x["age_months"] <= pension_age_months, True, False))
                  .assign(py_is_active=lambda x: np.where(x["is_active"], x["py"], 1))
                  .assign(py_is_alive_at_pensionage=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["py_is_active"].transform("prod"))
                  .assign(py_shifted = lambda df:  df.groupby(["gender", "age0_years", "month"], sort=False)["py"].shift().fillna(1))
                  .assign(py_year_fpa=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["py_shifted"].cumprod())
                  .assign(py_year_from_pensionage=lambda x: np.where(x["is_active"], 1, x["py_year_fpa"]/x["py_is_alive_at_pensionage"]))
                  .assign(py_year_from_pensionage_shifted=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["py_year_fpa"].shift(-1 * NMAANDEN_PER_JAAR).fillna(0))
                  .assign(py_year_from_pensionage_shifted=lambda x: np.where(x["is_active"], 1, x["py_year_from_pensionage_shifted"]/x["py_is_alive_at_pensionage"]))
                  .assign(avg=lambda x: np.where(x["is_year_transition"], (x["py_year_from_pensionage"] + x["py_year_from_pensionage_shifted"]) / 2, np.nan))
                  .assign(py_avg=lambda df: df.groupby(["gender", "age0_years", "month"], sort=False)["avg"].ffill())
                  .assign(py_year_avg=lambda x: np.where(x["age_months"]<= pension_age_months, 0, x["py_avg"]))
                  .assign(hx_modified=lambda x: x["hx_before_pd"] + x["py_year_avg"]) 
                        
                  # NPONBEPAALD
                  .assign(a_cumprod_reverse=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["py"]
                        .transform(lambda s: s.iloc[::-1].cumprod().iloc[::-1].to_numpy()))
                  .assign(a_cumprod_reverse_shifted=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["a_cumprod_reverse"].shift(-1).fillna(1))
                  .assign(b_shifted=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["payment_monthly"].shift().fillna(0))
                  .assign(product=lambda x: x["b_shifted"] * x["kqx"] * x["hx_modified"] * np.sqrt(x["py"]) * x["a_cumprod_reverse_shifted"])
                  .assign(cfs_unscaled=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["product"].cumsum())
                  .assign(cfs_pp_onbepaald=lambda x: x["cfs_unscaled"] / x["a_cumprod_reverse_shifted"])
                  .assign(cfs_pp_onbepaald=lambda x: x["cfs_pp_onbepaald"].fillna(0))
                  .assign(cfs_pp_onbepaald_discounted = lambda x: x["cfs_pp_onbepaald"] * x["discount_factor"]))
                  
            if lifelong_payments:
                  return (b
                        .rename(columns={"cfs_pp_onbepaald": label})
                        .loc[:, ["gender", "age0_years", "month", "index_nr", label]]
                        .set_index(["gender", "age0_years", "month", "index_nr"]))
            else:
                  return (b.copy()
                        # NPONBEP_uitgesteld
                        .assign(kqx_uitgesteld=lambda x:np.where((x["age_months"] <= pension_age_months), 0, x["kqx"]))
                        .assign(product_uitgesteld=lambda x: x["b_shifted"] * x["kqx_uitgesteld"] * x["hx_modified"] * np.sqrt(x["py"]) * x["a_cumprod_reverse_shifted"])
                        .assign(cfs_unscaled_uitgesteld=lambda d: d.groupby(["gender", "age0_years", "month"], sort=False)["product_uitgesteld"].cumsum())
                        .assign(cfs_pp_onbepaald_uitgesteld=lambda x: x["cfs_unscaled_uitgesteld"] / x["a_cumprod_reverse_shifted"])
                        .assign(cfs_pp_onbepaald_uitgesteld=lambda x: x["cfs_pp_onbepaald_uitgesteld"].fillna(0))
                        .assign(cfs_pp_onbepaald_discounted_uitgesteld = lambda x: x["cfs_pp_onbepaald_uitgesteld"] * x["discount_factor"])

                        # TNPONBEPAALD
                        .assign(cfs_tnponbepaald = lambda x: x["cfs_pp_onbepaald"] - x["cfs_pp_onbepaald_uitgesteld"])
                        .assign(cfs_tnponbepaald_discounted = lambda x: x["cfs_tnponbepaald"] * x["discount_factor"])
                        .rename(columns={"cfs_tnponbepaald": label})
                        .loc[:, ["gender", "age0_years", "month", "index_nr", label]]
                        .set_index(["gender", "age0_years", "month", "index_nr"]))


class TermInsurance:
      """
      Represents a term insurance calculation, with methods to compute the cash flows based on the provided (processed) data.
      """
      def __init__(self, processed_data: dict):  
            self.processed_data = processed_data
            
      def calculate_cfs(self, label: str="Ax", payments_start_age: int|None=None, payments_end_age: int|None=None, age_range: list|None=None) -> pd.Series:
            startleeftijd_uitkering_maanden = -np.inf if payments_start_age is None else (payments_start_age + 1 - self.processed_data.data["payout_is_praenumerando"])
            eindleeftijd_uitkering_maanden = np.inf if payments_end_age is None else payments_end_age

            if age_range:
                b = self.processed_data.base["df2"].query(f"age0_months.isin({age_range})") 
            else:
                b = self.processed_data.base["df2"] 
      
            return (b
                  .assign(has_payment = lambda x: (x["age_months"] >= startleeftijd_uitkering_maanden) & (x["age_months"] <= eindleeftijd_uitkering_maanden))
                  .assign(has_payment= lambda x: np.where(self.processed_data.data["payout_is_praenumerando"], x["has_payment"], (x["index_nr"] > 0) * x["has_payment"]))
                  .assign(payment_yearly=lambda x: np.where(x["has_payment"] & (x["index_nr"] % NMAANDEN_PER_JAAR == 0), 1, 0) * np.where(NMAANDEN_PER_JAAR * x["age_year_component"] == startleeftijd_uitkering_maanden, 0.5, 1))
                  .assign(payment_monthly=lambda x: np.where(x["has_payment"], 1/NMAANDEN_PER_JAAR, 0))
                  .assign(payment = lambda x: self.processed_data.data["payout_is_monthly"] * x["payment_monthly"] + (1 - self.processed_data.data["payout_is_monthly"]) * x["payment_yearly"])
                  .assign(cfs = lambda x: x["payment"] * x["kqx"] * x["step_function"] * NMAANDEN_PER_JAAR)
                  .rename(columns={"cfs": label})
                  .loc[:, ["gender", "age0_years", "month", "index_nr", label]]
                  .set_index(["gender", "age0_years", "month", "index_nr"])
                  )
 