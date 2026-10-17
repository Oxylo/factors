import numpy as np
import pandas as pd
from utils import (convert_yearly_to_monthly,
                   calculate_forward_rate_yearly,
                   preprocess,
                   normalize,
                   get_uniques_per_group
                   )
from system_settings import NMAANDEN_PER_JAAR, DEFAULT_PENSION_AGE_MONTHS


class UninitializedStateException(RuntimeError):
    """Exception raised when methods are called out of order."""


class PreProcessor:
      """
      Holds source data and settings for the cashflow calculations and offers some data preprocessing utilities.

      Parameters:
      data (dict): A dictionary containing the following pandas Dataframes: qx, qy, es, hxy, rts plus the following settings: start_year, delta_x_y_months, delta_x_y_months, payout_is_monthly, spreading_period, payout_is_praenuemrando
      """
      def __init__(self, data: dict):
            self.data = data
            self.base = self.calculate_base()
            self.discount = self.calculate_discount()

      def normalize_data(self) -> dict:
            return normalize(self.data)

      def calculate_base(self) -> dict:
            normalized_data = self.normalize_data()
            frm = convert_yearly_to_monthly(calculate_forward_rate_yearly(self.data["interest_curve"].set_index("looptijd_jaren")["pct_rente"]))
            return preprocess(normalized_data, frm)

      def calculate_discount(self) -> pd.DataFrame:
           fw_rates = convert_yearly_to_monthly(calculate_forward_rate_yearly(self.data["interest_curve"].set_index("looptijd_jaren")["pct_rente"]))
           return fw_rates.assign(discount_factor=lambda x: (1 + x["spot_rate_monthly"])**(-1 * x.index))["discount_factor"]


class Insurance:
      """
      Generate cashflows per insurcance type, based on the provided (processed) data.
      """
      def __init__(self, processed_data: dict):  
            self.processed_data = processed_data
            self.store_cashflows = None
            self.store_factors = None
            self.store_base = {}

      # 1. Annuities
            
      def cfs_annuity(self, label: str="ax", payments_start_age: int|None=None, payments_end_age: int|None=None, two_lives: bool=False, age_range: list|None=None) -> pd.Series:
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
                  .assign(cfs = lambda x: x["prob_alive"] * x["payment"])
                  .rename(columns={"cfs": label})
                  .loc[:, ["gender", "age0_months", "index_nr", label]]
                  .set_index(["gender", "age0_months", "index_nr"])
                  )


      # 2. Partner Pension
            
      def cfs_partner_pension_determined(self, label: str="ax|y", payments_start_age: int|None=None, payments_end_age: int|None=None, age_range: list|None=None) -> pd.Series:
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
                  .assign(cfs_axy = lambda x: x["npxy"] * x["payment"])
                  .assign(cfs_ay = lambda x: x["npy"] * x["payment_ever"] * np.where((1 - self.processed_data.data["payout_is_monthly"]) * (x["index_nr"] == 0), 0.5, 1))
                  .assign(cfs_ay_discounted = lambda x: x["cfs_ay"] * x["discount_factor"])
                  .assign(cfs = lambda x: np.where(x["has_payment"], x["cfs_ay"] - x["cfs_axy"], 0))
                  .assign(cfs = lambda x: (1 - self.processed_data.data["payout_is_praenumerando"]) * (x["index_nr"] > 0) * x["cfs"])  # Deze regel moet er waarschijnlijk uit, want partnerpensioen is altijd postnumerando, dus geen betaling bij index_nr = 0
                  .rename(columns={"cfs": label})
                  .loc[:, ["gender", "age0_months", "index_nr", label]]
                  .set_index(["gender", "age0_months", "index_nr"])
                  )

      def cfs_partner_pension_indetermined(self, label: str="ax|yh", pension_age_months: int=DEFAULT_PENSION_AGE_MONTHS, lifelong_payments: bool=True, age_range: list|None=None) -> pd.Series:

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
                        .loc[:, ["gender", "age0_months", "index_nr", label]]
                        .set_index(["gender", "age0_months", "index_nr"]))
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
                        .loc[:, ["gender", "age0_months", "index_nr", label]]
                        .set_index(["gender", "age0_months", "index_nr"]))

      # 3. Term insurance

            
      def cfs_terminsurance(self, label: str="Ax", payments_start_age: int|None=None, payments_end_age: int|None=None, age_range: list|None=None) -> pd.Series:
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
                  .assign(cfs = lambda x: x["payment"] * x["kqx"] * NMAANDEN_PER_JAAR)
                  .rename(columns={"cfs": label})
                  .loc[:, ["gender", "age0_months", "index_nr", label]]
                  .set_index(["gender", "age0_months", "index_nr"]))

      # By individual insurance type    

      def calculate_cfs(self, insurance_type: str, pe_age_range: list):
           allowed_insurance_types = ("OP", "AX", "AXN", "AXY", "NPBEPAALD", "TNPBEPAALD", "NPONBEPAALD", "TNPONBEPAALD", "SG_OP", "SG_AX", "SG_AXN")
           if not insurance_type in allowed_insurance_types:
                raise ValueError(f"Insurance type should be in {allowed_insurance_types}")

           new_dex = ["insurance_type", "pe_age", "age0_months", "gender", "index_nr"]
           outp = len(pe_age_range) * [np.nan]

           match insurance_type:
                     
                case "OP":
                     for i, pe in enumerate(pe_age_range):
                        cf = self.cfs_annuity(label="cfs", payments_start_age=pe)
                        outp[i] = cf.reset_index().assign(pe_age=pe, insurance_type="OP").set_index(new_dex)
                     return pd.concat(outp)
             
                case "AX":
                     for i, pe in enumerate(pe_age_range):
                        cf = self.cfs_annuity(label="cfs")
                        outp[i] = cf.reset_index().assign(pe_age=pe, insurance_type="AX").set_index(new_dex)
                     return pd.concat(outp)
 
                case "AXN":
                     for i, pe in enumerate(pe_age_range):
                        cf = self.cfs_annuity(label="cfs", payments_end_age=pe)
                        outp[i] = cf.reset_index().assign(pe_age=pe, insurance_type="AXN").set_index(new_dex)
                     return pd.concat(outp)

                case "AXY":
                     for i, pe in enumerate(pe_age_range):
                        cf = self.cfs_annuity(label="cfs", two_lives=True)
                        outp[i] = cf.reset_index().assign(pe_age=pe, insurance_type="AXY").set_index(new_dex)
                     return pd.concat(outp)

                case "NPBEPAALD":
                     for i, pe in enumerate(pe_age_range):
                        cf = self.cfs_partner_pension_determined(label="cfs")
                        outp[i] = cf.reset_index().assign(pe_age=pe, insurance_type="NPBEPAALD").set_index(new_dex)
                     return pd.concat(outp)
                      
                case "TNPBEPAALD":
                     for i, pe in enumerate(pe_age_range):
                        cf = self.cfs_partner_pension_determined(label="cfs", payments_end_age=pe)
                        outp[i] = cf.reset_index().assign(pe_age=pe, insurance_type="TNPBEPAALD").set_index(new_dex)
                     return pd.concat(outp)
                     
                case "NPONBEPAALD":
                     for i, pe in enumerate(pe_age_range):
                        cf = self.cfs_partner_pension_indetermined(label="cfs", pension_age_months=pe)
                        outp[i] = cf.reset_index().assign(pe_age=pe, insurance_type="NPONBEPAALD").set_index(new_dex)
                     return pd.concat(outp)
                     
                case "TNPONBEPAALD":
                     for i, pe in enumerate(pe_age_range):
                        cf = self.cfs_partner_pension_indetermined(label="cfs", pension_age_months=pe, lifelong_payments=False)
                        outp[i] = cf.reset_index().assign(pe_age=pe, insurance_type="TNPONBEPAALD").set_index(new_dex)
                     return pd.concat(outp)
                     
                case "SG_OP":
                     for i, pe in enumerate(pe_age_range):
                        cf = self.cfs_terminsurance(label="cfs", payments_start_age=pe)
                        outp[i] = cf.reset_index().assign(pe_age=pe, insurance_type="SG_OP").set_index(new_dex)
                     return pd.concat(outp)
                     
                case "SG_AX":
                     for i, pe in enumerate(pe_age_range):
                        cf = self.cfs_terminsurance(label="cfs")
                        outp[i] = cf.reset_index().assign(pe_age=pe, insurance_type="SG_AX").set_index(new_dex)
                     return pd.concat(outp)
                     
                case "SG_AXN":
                     for i, pe in enumerate(pe_age_range):
                        cf = self.cfs_terminsurance(label="cfs", payments_end_age=pe)
                        outp[i] = cf.reset_index().assign(pe_age=pe, insurance_type="SG_AXN").set_index(new_dex)
                     return pd.concat(outp)

      def cfs_old(self, pe_ages_per_insurance_type: dict) -> pd.DataFrame:
           self.store_cashflows = pd.concat([self.calculate_cfs(insurance_type=k, pe_age_range=v) for k, v in pe_ages_per_insurance_type.items()])
           return self.store_cashflows
      
      
      
      def validate_selection(self, selection) -> None:
           allowed_insurance_types = ("OP", "AX", "AXN", "AXY", "NPONBEPAALD", "TNPONBEPAALD", "NPBEPAALD", "TNPBEPAALD", "SG_OP", "SG_AX", "SG_AXN")
           required_individual_keys = ("age0_months", "pe_age", "insurance_type")
           
           is_df = isinstance(selection, pd.DataFrame)
           if isinstance(selection, dict):
                is_dict_pe_ages = all(item in allowed_insurance_types for item in selection.keys()) & all(isinstance(item, list) for item in selection.values()) 
                is_dict_individual_case = all(item in required_individual_keys for item in selection.keys())
           else:
                is_dict_pe_ages = False
                is_dict_individual_case = False 
      
           if not any([is_df, is_dict_pe_ages, is_dict_individual_case]):
               raise TypeError("Invalid parameter 'selection'.\n"
                               "---------------------------------\n"
                               f"- 1 specific factor? --> use dict containing {required_individual_keys} as keys and scalar as values\n"
                               f"- own selection of factors? --> use DataFrame containing the columns: {required_individual_keys}\n" 
                               f"- all factors? --> dict containing at least one of the keys {allowed_insurance_types} and list as values")
           if is_dict_individual_case:
                return "individual"
           if is_df:
                return "own selection"
           if is_dict_pe_ages:
                return "all factors" 
                    
      
      def cfs(self, selection: pd.DataFrame|dict|None=None) -> pd.DataFrame:

          validation_outcome = self.validate_selection(selection)

          match validation_outcome:
               case "individual":
                    individual_case = pd.DataFrame(data={k: 2*[v] for k, v in selection.items()}).assign(gender=["M", "F"])
                    self.update_base(individual_case)
                    pe_ages_per_insurance_type = {selection["insurance_type"]: [selection["pe_age"]]}
               case "own selection":
                    self.update_base(selection.drop_duplicates(subset=["age0_months", "gender"]))
                    pe_ages_per_insurance_type = get_uniques_per_group(selection[["insurance_type", "pe_age"]])
               case "all factors":
                    pe_ages_per_insurance_type = selection
                                                   
          self.store_cashflows = pd.concat([self.calculate_cfs(insurance_type=k, pe_age_range=v) for k, v in pe_ages_per_insurance_type.items()])
          return self.store_cashflows

      def update_base(self, selection: pd.DataFrame|None=None) -> pd.DataFrame:

           if not self.store_base:
                self.store_base["df2"] = self.processed_data.base["df2"].copy()
                self.store_base["df2_xy"] = self.processed_data.base["df2_xy"].copy()
           
           self.processed_data.base["df2"] = self.store_base["df2"].merge(selection, on=["age0_months", "gender"])
           self.processed_data.base["df2_xy"] = self.store_base["df2_xy"].merge(selection, on=["age0_months", "gender"])
     
                
      def factors(self) -> pd.DataFrame:
           if self.store_cashflows is None:
                raise UninitializedStateException("Calculate cashflows first using the .cfs() method.")
           else:
                
                self.store_factors = (self.store_cashflows
                           .merge(self.processed_data.discount, left_on="index_nr", right_index=True, how="left")
                           .merge(self.stepfunction, left_on="index_nr", right_index=True, how="left")
                           .fillna(1)
                           .assign(factor=lambda x: x["cfs"] * x["discount_factor"])
                           .assign(factor_stepped=lambda x: x["factor"] * x["step_function"])
                           .groupby(["insurance_type", "pe_age", "age0_months", "gender"])[["factor", "factor_stepped"]]
                           .sum())

                unstacked = self.store_factors.unstack()
                column_labels = ["_".join(item) for item in unstacked.columns]
                unstacked.columns = column_labels
                return unstacked.reset_index().loc[:, ["insurance_type", "age0_months", "pe_age", "factor_M", "factor_F", "factor_stepped_M", "factor_stepped_F"]]

      @property
      def stepfunction(self):
           b = self.store_base["df2"] if self.store_base else self.processed_data.base["df2"]
           return b.query("(age0_months==0) & (gender=='M')").loc[:, ["index_nr", "step_function"]].set_index("index_nr")
           
     

                

                     
                     

           
                

                  
 