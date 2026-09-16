from utils import calculate_forward_rate_yearly, read_workbook, explode


fp = "/home/pieter/Insync/Gedeeld/QuantSense/Innovatie en Inspiratie/tarievengenerator/rail26.xlsx"

data = read_workbook(fp)

forward_rate_yearly = calculate_forward_rate_yearly(
    data["rts"].set_index("looptijd_jaren")["pct_rente"]
)

explode(forward_rate_yearly, explode_factor=12).reset_index().assign(forward_rate_yearly_factor = lambda row: 1 + row["forward_rate_yearly"]).assign(product=lambda row: row["forward_rate_yearly_factor"].cumprod().assign())
