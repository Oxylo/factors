import numpy as np
import pandas as pd

test_data = (np.array([
[88, 14, 97, 59],
[48, 42,  1, 34],
[92, 70, 49, 35],
[43, 76, 79, 39],
[25, 67, 18,  2]]
))

df = pd.DataFrame(test_data, columns=list("abcd"))

r = (df.assign(a_cumprod_reverse=lambda x: x["a"][::-1].cumprod()[::-1].values)
   .assign(a_cumprod_reverse_shifted=lambda x: x["a_cumprod_reverse"].shift(-1).fillna(1))
   .assign(b_shifted = lambda x: x["b"].shift().fillna(0))
   .assign(product=lambda x: x["b_shifted"] * x["c"] * x["d"] * np.sqrt(x["a"]) * x["a_cumprod_reverse_shifted"])
   .assign(cf_unscaled=lambda x: x["product"].cumsum())
   .assign(cf_pp_onbepaald=lambda x: x["cf_unscaled"] / x["a_cumprod_reverse_shifted"])
)
 				


df_test = pd.DataFrame({"grp": ["A", "A", "A", "B", "B"], "value": [4, 10, 2, 8, 70]})

df_test