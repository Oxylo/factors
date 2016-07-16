import sys
sys.path.append('/home/pieter/projects/factors')

from models import LifeTable
from utils import to_excel

if __name__ == '__main__':
    tab = LifeTable('AEG2011')

    # run test
    # testresults = tab.run_test()
    # to_excel(testresults, 'testresults.xlsx')

    # generate factors
    tab.export('AegonFactors.xlsx', intrest=3, pension_age=67)
