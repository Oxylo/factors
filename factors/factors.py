import sys
sys.path.append('/home/pieter/projects/factors')
import pandas as pd

from models import LifeTable
from utils import cartesian, to_excel, expand

tab = LifeTable('AEG2011')

insurance_ids = ['OPLL', 'NPLL-B', 'NPLL-O', 'NPLLRS',
                 'NPTL-B', 'NPTL-O', 'ay_avg']
intrest = 3
pension_age = 67

# run test
# testresults = tab.run_test()
# to_excel(testresults, 'testresults.xlsx')

# create table layout with all desired tariff combinations
df = cartesian(lists=[insurance_ids, ['M', 'F'], range(15, 70)],
               colnames=['insurance_id', 'sex_insured', 'age_insured'])


# generate cashflows
def map_to_cf(row):
    return tab.cf(insurance_id=row['insurance_id'],
                  age_insured=row['age_insured'],
                  sex_insured=row['sex_insured'],
                  pension_age=pension_age,
                  intrest=intrest)
df['cf'] = df.apply(map_to_cf, axis=1)

temp = df.copy(deep=True)
temp['cf'] = temp['cf'].map(lambda x: x['payments'])


# calculate present values (=generating tariff table)
df['tar'] = df.apply(lambda row: tab.pv(row['cf'], intrest=intrest), axis=1)
df.set_index(['insurance_id', 'sex_insured', 'age_insured'], inplace=True)
df.drop('cf', inplace=True, axis=1)

# export results to Excel

# sheet1. legend with description for given insurance id's
df1 = pd.read_excel('/home/pieter/projects/factors/data/lifedb.xls',
                    sheetname='tbl_insurance_types')
df1.set_index('id_type', inplace=True)
df1 = df1.ix[insurance_ids]

# sheet2 tar factors
df2 = df
df2 = df2.unstack(['sex_insured', 'insurance_id'])

# sheet3 cashflows
df3 = expand(temp, 'cf')
df3.set_index(['sex_insured', 'insurance_id', 'age_insured', 'year'], inplace=True)
df3 = df3.unstack(['sex_insured', 'insurance_id'])

# sheet4 yield curce
df4 = pd.DataFrame(data=120 * [intrest],
                   columns=['intrest'])

# sheet5 lx
df5 = pd.concat([tab.lx['M'], tab.lx['F']], axis=1)

# sheet6 hx
df6 = pd.concat([tab.hx['M'], tab.hx['F']], axis=1)

# sheet7 adjustments
df7 = pd.read_excel('/home/pieter/projects/factors/data/lifedb.xls',
                    sheetname='tbl_adjustments')
df7 = df7[df7['id'] == 2]  # Ugly! still hard coded!

# write everything to Excel
writer = pd.ExcelWriter('results.xlsx')
df1.to_excel(writer, 'legend')
df2.to_excel(writer, 'tar')
df3.to_excel(writer, 'cashflows')
df4.to_excel(writer, 'yield_curve')
df5.to_excel(writer, 'lx')
df6.to_excel(writer, 'hx')
df7.to_excel(writer, 'adjustments', index=False)
writer.save()

print("Ready!")
