from __future__ import print_function

from collections import OrderedDict

import numpy as np
import pandas as pd
import xlrd

from factors.settings import (UPAGE, LOWAGE, MAXAGE, INSURANCE_IDS,
                              MALE, FEMALE, DATADIR)
from factors.utils import (dictify, get_excel_filepath,
                           prae_to_continuous, merge_two_dicts,
                           cartesian, expand, x_to_series)
from factors.utils_extra import (read_generation_table,
                                 flatten_generation_table)

REQUIRED_SHEETS = [
    'tbl_insurance_types',
    'tbl_tariff',
    'tbl_lx',
    'tbl_hx',
    'tbl_adjustments'
]  # optional: tbl_ukv and tbl_testdata


def get_available_tablenames():
    df = pd.read_csv(DATADIR + "/tables.csv")
    print(df.to_string(index=False))


class LifeTable(object):
    def __init__(self, tablename, **kwargs):
        self.tablename = tablename
        self.excel_filepath = get_excel_filepath(tablename=tablename)
        msg = "Reading table parmeters from {}"
        print(msg.format(self.excel_filepath))
        # TODO: make calc_year required if type(tablename) = generation
        self.calc_year = kwargs.get('calc_year', 2017)
        self.legend = self.get_legend()
        self.params = self.get_parameters()
        self.generation_table = self.read_generation_table()
        self.sheet_names = self.get_sheet_names()
        self.lx_table = self.get_lx_table()
        self.lx = self.get_lx  # no call as this function is called later!
        self.hx = self.get_hx()
        self.adjust = self.get_adjustments()
        self.ukv = self.get_ukv() if 'tbl_ukv' in self.get_sheet_names() else None
        self.testdata = self.get_testdata() if 'tbl_testdata' in self.get_sheet_names() else None
        self.pension_age = None
        self.intrest = None
        self.lookup = None
        self.cfs = None
        self.factors = None
        self.yield_curve = None

    def get_sheet_names(self):
        wb = xlrd.open_workbook(self.excel_filepath, on_demand=True)
        return wb.sheet_names()

    def xls_contains_all_required_sheets(self):
        return all(x in self.sheet_names for x in REQUIRED_SHEETS)

    def get_legend(self):
        sheet = 'tbl_insurance_types'
        # TODO : Python 2 verwacht sheetname=sheet
        df = pd.read_excel(self.excel_filepath, sheet_name=sheet)
        df.set_index('id_type', inplace=True)
        return df

    def get_parameters(self):
        sheet = 'tbl_tariff'
        # TODO : Python 2 verwacht sheetname=sheet
        df = pd.read_excel(self.excel_filepath, sheet_name=sheet)
        # to_dict("records") converts it to a list of dictionaries,
        # we just want the first item
        parameters = df.to_dict("records")
        if len(parameters) != 1:
            raise ValueError("Parameters has an incorrect format")
        return parameters[0]

    def read_generation_table(self):
        if self.params['is_flat']:
            return None
        else:
            return read_generation_table(self.excel_filepath,
                                         self.params['lx'],
                                         self.calc_year)

    def get_lx_table(self):
        if self.params['is_flat']:
            sheet = 'tbl_lx'
            # TODO : Python 2 verwacht sheetname=sheet
            df = pd.read_excel(self.excel_filepath, sheet_name=sheet)
            df.set_index(['gender', 'age'], inplace=True)
            out = {gender: df.ix[gender] for gender in (MALE, FEMALE)}
        else:
            out = flatten_generation_table(self.generation_table)
        return out

    def get_lx(self, current_age):
        """ Return lx_table for given current age
        """
        if self.params['is_flat']:
            out = self.lx_table
        else:
            out = {gender: self.lx_table[gender].ix[current_age] for gender in [MALE, FEMALE]}
        return out

    def get_hx(self):
        sheet = 'tbl_hx'
        # TODO : Python 2 verwacht sheetname=sheet
        df = pd.read_excel(self.excel_filepath, sheet_name=sheet)
        df.set_index(['gender', 'age'], inplace=True)
        return {gender: df.ix[gender] for gender in (MALE, FEMALE)}

    def get_adjustments(self):
        sheet = 'tbl_adjustments'
        # TODO : Python 2 verwacht sheetname=sheet
        df = pd.read_excel(self.excel_filepath, sheet_name=sheet)
        return dictify(df)

    def get_ukv(self):
        sheet = 'tbl_ukv'
        # TODO : Python 2 verwacht sheetname=sheet
        df = pd.read_excel(self.excel_filepath, sheet_name=sheet)
        df.set_index(['gender', 'pension_age', 'intrest'], inplace=True)
        return df

    def get_testdata(self):
        sheet = 'tbl_testdata'
        # TODO : Python 2 verwacht sheetname=sheet
        return pd.read_excel(self.excel_filepath, sheet_name=sheet)

    def npx(self, age, sex, nyears):
        """Returns probability person with given age is still alive after n years.

        Parameters:
        -----------
        age: int
        sex: either 'M' of 'F'
        nyears: int
        """
        future_age = np.minimum(age + nyears, MAXAGE)
        current_age = np.minimum(age, MAXAGE)
        lx = self.lx(current_age)
        return (float(lx[sex].ix[future_age]['lx']) /
                lx[sex].ix[current_age]['lx'])

    def qx(self, age, sex):
        """Returns the probability that person with given age will die within 1 year.

        Parameters:
        -----------
        age: int
        sex: either 'M' of 'F'
        """
        return 1 - self.npx(age, sex, 1)

    def nqx(self, age, sex, nyears):
        """Returns probability that person with will die
           in interval (nyears - 1, nyears).

        Parameters:
        -----------
        age: int
        sex: either 'M' of 'F'
        nyears: int
        """
        return self.npx(age, sex, nyears - 1) - self.npx(age, sex, nyears)


    def cf_annuity(self, age, lx, defer=0):
        """ Returns expected payments for (deferred) lifetime annuity.

        Parameters:
        -----------
        age: int
        lx: series
        defer: int
        """
        nrows = len(lx)
        assert nrows > defer, "Error: deferral period exceeds number of table rows."
        age = int(age)  # We can't index with floats
        payments = pd.Series(defer * [0] + (nrows - defer) * [1])
        out = (payments * lx.shift(-age) / lx.ix[age]).fillna(0)
        out.index.rename('year', inplace=True)
        return out

    def cf_ay_avg(self, age_insured, sex_insured, pension_age=None, **kwargs):
        """ Returns cash flows non-defered annuity for beneficiary.

        Parameters:
        ----------
        age_insured: int
        sex_insured: either 'M' of 'F'

        insurance_type: either 'partner' or 'risk. Default 'partner'
        """
        insurance_type = kwargs.get('insurance_type', 'partner')
        assert sex_insured in (MALE, FEMALE), "sex insured should be either M of F!"
        sex_beneficiary = FEMALE if sex_insured == MALE else MALE
        delta = int(self.params['delta'])
        sign = 1 if sex_insured == MALE else -1
        gamma3 = self.adjust[sex_beneficiary][insurance_type]['CX3']
        current_age_beneficiary = age_insured - sign * delta + gamma3
        lx = self.lx(current_age_beneficiary)
        tbl_beneficiary = (lx[FEMALE]['lx'] if sex_insured == MALE
        else lx[MALE]['lx'])
        cf_ay_avg = (self.cf_annuity(current_age_beneficiary,
                                     tbl_beneficiary) + self.cf_annuity(
            current_age_beneficiary + 1, tbl_beneficiary)) / 2.
        cf_ay_avg = prae_to_continuous(cf_ay_avg)
        return {'payments': cf_ay_avg}

    def ay_avg(self, age_insured, sex_insured,
               intrest, insurance_type='partner', rounding=False):
        """ Returns single premium non-defered annuity for beneficiary.

        Parameters:
        ----------
        age_insured: int
        sex_insured: either 'M' of 'F'
        intrest: int, float or Series
        (example: for calculating with 3.2 percent intrest rate, intrest=3.2)

        insurance_type: either 'partner' or 'risk'. Default 'partner'.
        """
        cf_ay_avg = self.cf_ay_avg(age_insured, sex_insured, insurance_type)
        return self.pv({'insurance_id': 'OPLL',
                        'payments': cf_ay_avg['payments']}, intrest, rounding)

    def create_lookup_table(self, intrest):
        """ Returns a lookup table with age/sex dependent items for undefined partner.

        Parameters:
        -----------
        intrest: int, float of Series.
        """
        s = pd.DataFrame({'gender': (UPAGE - LOWAGE) * [MALE] +
                                    (UPAGE - LOWAGE) * [FEMALE],
                          'age': np.concatenate([np.arange(LOWAGE, UPAGE), np.arange(LOWAGE, UPAGE)])
                          })
        s['ay_avg'] = s.apply(lambda row: self.ay_avg(row['age'],
                                                      row['gender'],
                                                      intrest,
                                                      rounding=False), axis=1)
        s['hx_avg'] = s.apply(lambda row: (self.hx[row['gender']].ix[row['age']].values[0] +
                                           self.hx[row['gender']].ix[row['age'] + 1].values[0]) / 2., axis=1)
        s['alpha1'] = s.apply(lambda row: self.adjust[row['gender']]['partner']['CX1'], axis=1)
        s['factor'] = s.apply(lambda row: self.adjust[row['gender']]['partner']['fnett'] *
                                          self.adjust[row['gender']]['partner']['fcorr'] *
                                          self.adjust[row['gender']]['partner']['fOTS'],
                              axis=1)
        s['cf'] = s['ay_avg'] * s['hx_avg'] * s['factor']
        s.set_index(['gender', 'age'], inplace=True)
        return s

    def cf_retirement_pension(self, age_insured, sex_insured,
                              pension_age, **kwargs):
        """ Returns expected payments retirement pension.

        Parameters:
        -----------
        age_insured: int
        sex_insured: either 'M' of 'F'
        pension_age: int

        postnumerando: boolean
        """
        postnumerando = (kwargs['postnumerando'] if
        'postnumerando' in kwargs else False)

        alpha1 = self.adjust[sex_insured]['retire']['CX1']
        alpha2 = self.adjust[sex_insured]['retire']['CX2']
        lx = self.lx(age_insured + alpha2)
        tbl_insured = lx[sex_insured]['lx']
        fnett, fcorr, fOTS = (self.adjust[sex_insured]['retire'][item]
                              for item in ['fnett', 'fcorr', 'fOTS'])
        cf = self.cf_annuity(age_insured + alpha2, tbl_insured,
                             defer=pension_age - age_insured + postnumerando)
        cf = cf * self.npx(age_insured + alpha1, sex_insured,
                           pension_age - age_insured)
        cf = cf / self.npx(age_insured + alpha2, sex_insured,
                           pension_age - age_insured)
        cf = prae_to_continuous(cf)
        return {'payments': cf * fnett * fcorr * fOTS}

    def cf_defined_partner(self, age_insured, sex_insured,
                           pension_age, **kwargs):
        """ Returns expected payments partner pension (defined partner).

        Parameters:
        ----------
        age_insured: int
        sex_insured: either 'M' of 'F'
        pension_age: int
        """
        assert sex_insured in (MALE, FEMALE), "sex insured should be either M of F!"
        sex_beneficiary = FEMALE if sex_insured == MALE else MALE

        alpha1 = self.adjust[sex_insured]['partner']['CX1']
        alpha2 = self.adjust[sex_insured]['partner']['CX2']
        gamma3 = self.adjust[sex_beneficiary]['partner']['CX3']
        sign = 1 if sex_insured == MALE else -1
        delta = int(self.params['delta'])

        current_age_alpha1 = age_insured + alpha1
        current_age_alpha2 = age_insured + alpha2
        current_age_beneficiary = age_insured - sign * delta + gamma3

        lx_insured_alpha1 = self.lx(current_age_alpha1)
        lx_insured_alpha2 = self.lx(current_age_alpha2)
        lx_beneficiary = self.lx(current_age_beneficiary)

        tbl_insured_alpha1 = lx_insured_alpha1[sex_insured]['lx']
        tbl_insured_alpha2 = lx_insured_alpha2[sex_insured]['lx']
        tbl_beneficiary = lx_beneficiary[sex_beneficiary]['lx']

        fnett, fcorr, fOTS = (self.adjust[sex_insured]['partner'][item]
                              for item in ['fnett', 'fcorr', 'fOTS'])

        ay = self.cf_annuity(current_age_beneficiary,
                             tbl_beneficiary)
        ax = self.cf_annuity(current_age_alpha1, tbl_insured_alpha1)
        axy = ax.multiply(ay)

        f1 = self.cf_annuity(current_age_alpha1, tbl_insured_alpha1,
                             pension_age - age_insured)
        f1 = f1 * self.cf_annuity(current_age_beneficiary,
                                  tbl_beneficiary, pension_age - age_insured)
        f2 = self.cf_annuity(current_age_alpha2,
                             tbl_insured_alpha2, pension_age - age_insured)
        f2 = f2 * self.cf_annuity(current_age_beneficiary,
                                  tbl_beneficiary, pension_age - age_insured)
        temp1 = ((float(tbl_insured_alpha1.ix[pension_age + alpha1]) /
                  tbl_insured_alpha1.ix[current_age_alpha1]))
        temp2 = ((float(tbl_insured_alpha2.ix[current_age_alpha2]) /
                  tbl_insured_alpha2.ix[pension_age + alpha2]))
        f2 = f2 * temp1 * temp2
        out = fnett * fcorr * fOTS * (ay - axy + (f1 - f2))
        # print(ay, axy, f1, f2)
        return {'payments': out}

    def cf_undefined_partner(self, age_insured, sex_insured,
                             pension_age, **kwargs):
        """ Returns expected payments partner pension (undefined partner).

        TO DO: intrest or yield curve really required to get cash flows
        undefined partner?

        Parameters:
        ----------
        age_insured: int
        sex_insured: either 'M' of 'F'
        pension_age: int

        intrest: float, series or list. Default = 3 pct!
        hx_pd: either 'None' for non-exchangable, 'one' for exchangable
        or 'ukv' for Aegon methodology (depreciated).

        """
        assert sex_insured in (MALE, FEMALE), "sex insured should be either M of F!"

        intrest = kwargs.get('intrest', None)
        if (intrest is None):
            msg1 = "Undefined partner cashflows require intrest"
            msg2 = "-- defaults intrest = 3pct"
            print("{0} {1}".format(msg1, msg2))
            intrest = 3  # default = 3 pct intrest rate!

        hx_pd = kwargs.get('hx_pd', None)
        # by default, undefined partner pension is assumed to be exchangable
        if (hx_pd is None) or (hx_pd == 'one'):
            hx_at_pensionage = 1
        elif hx_pd == 'ukv':
            try:
                hx_at_pensionage = self.ukv.ix[(sex_insured, pension_age,
                                                kwargs['intrest'])].values[0]
            except:
                print('Undefined partner cashflows require UKV -- defaults hx_pd = 1')
                hx_at_pensionage = 1
        else:
            hx_at_pensionage = self.hx[sex_insured]['hx'].ix[pension_age]

        fnett, fcorr, fOTS = (self.adjust[sex_insured]['partner'][item]
                              for item in ['fnett', 'fcorr', 'fOTS'])

        # cf till retirement
        if intrest == self.intrest:
            lookup = self.lookup
        else:
            lookup = self.create_lookup_table(intrest)
            self.lookup = lookup
            self.intrest = intrest

        cf_till_pension_age = (lookup.ix[sex_insured].
                                   ix[age_insured:pension_age - 1])
        current_age = age_insured  # we need [k]q[current_age]
        cf_till_pension_age['age'] = cf_till_pension_age.index
        nq_current_age = cf_till_pension_age.apply(lambda row:
                                                   self.nqx(current_age + row['alpha1'],
                                                            sex_insured,
                                                            row['age'] - current_age + 1),
                                                   axis=1)
        cf_till_pension_age = cf_till_pension_age['cf'] * nq_current_age
        cf_till_pension_age = pd.DataFrame(cf_till_pension_age, columns=['cf'])

        # cf after retirement
        prob = self.npx(age_insured + lookup['alpha1'].loc[(sex_insured, age_insured)], sex_insured,
                        pension_age - age_insured)
        cf_defined_partner = self.cf_defined_partner(pension_age, sex_insured, pension_age)
        cf_after_pension_age = hx_at_pensionage * prob * cf_defined_partner['payments']
        cf_after_pension_age = pd.DataFrame(cf_after_pension_age, columns=['cf'])
        cf_after_pension_age['age'] = cf_after_pension_age.index + pension_age
        cf_after_pension_age.set_index('age', inplace=True)
        cf = cf_till_pension_age.append(cf_after_pension_age)
        cf = pd.DataFrame(cf)
        cf['year'] = range(len(cf))
        cf.set_index('year', inplace=True)
        cf = pd.Series(cf['cf'])
        return {'age': age_insured, 'pension_age': pension_age, 'payments': cf}

    def cf_defined_one_year_risk(self, age_insured, sex_insured, pension_age, **kwargs):
        """ Ruturns expected cashflows one year risk premium (defined partner).

        ----------
        Parameters:
        ----------
        age_insured: int
        sex_insured: either 'M' of 'F'
        pension_age: int
        """
        # alpha1 = self.adjust[sex_insured]['risk']['CX1']
        # fnett, fcorr, fOTS = (self.adjust[sex_insured]['risk'][item]
        #                      for item in ['fnett', 'fcorr', 'fOTS'])
        #  --- risk premiums are considered to be part of partnerpension, so its adjustments are used! ---
        alpha1 = self.adjust[sex_insured]['partner']['CX1']
        fnett, fcorr, fOTS = (self.adjust[sex_insured]['partner'][item]
                              for item in ['fnett', 'fcorr', 'fOTS'])
        assert sex_insured in (MALE, FEMALE), "sex insured should be either M of F!"

        cf = self.cf_ay_avg(age_insured, sex_insured, insurance_type='partner')
        qx = self.qx(age_insured + alpha1, sex_insured)
        cf = cf['payments'] * qx * fnett * fcorr * fOTS
        return {'insurance_id': 'NPTL-B', 'payments': cf}

    def cf_undefined_one_year_risk(self, age_insured, sex_insured, pension_age, **kwargs):
        """ Ruturns expected cashflows one year risk premium (undefined partner).

        ----------
        Parameters:
        ----------
        age_insured: int
        sex_insured: either 'M' of 'F'
        pension_age: int
        """

        hx_avg = (self.hx[sex_insured].ix[age_insured].values[0] + self.hx[sex_insured].ix[age_insured + 1].values[
            0]) / 2.
        cf_defined_one_year_risk = self.cf_defined_one_year_risk(age_insured, sex_insured, pension_age, **kwargs)
        cf = hx_avg * cf_defined_one_year_risk['payments']
        return {'insurance_id': 'NPTL-O', 'payments': cf}

    def cf(self, insurance_id, age_insured, sex_insured, pension_age, **kwargs):
        """ Returns cash flows for given insurance type.

        Parameters:
        -----------
        insurance_id: either 'OPLL', 'NPLL-B', 'NPLL-O', 'NPLLRS', 'NPLLRU', 'NPTL-B' or 'NPTL-O'
        age_insured: int
        sex_insured: either 'M' of 'F'
        pension_age: int

        intrest: int, float or Series. Optional. Default 3pct.
        """

        switcher = {'OPLL': {'call': self.cf_retirement_pension, 'hx_pd': None},
                    'NPLL-B': {'call': self.cf_defined_partner, 'hx_pd': None},
                    'NPLL-O': {'call': self.cf_undefined_partner, 'hx_pd': 'non-exchangable'},
                    'NPLLRS': {'call': self.cf_undefined_partner, 'hx_pd': 'one'},
                    'NPLLRU': {'call': self.cf_undefined_partner, 'hx_pd': 'ukv'},
                    'NPTL-B': {'call': self.cf_defined_one_year_risk, 'hx_pd': None},
                    'NPTL-O': {'call': self.cf_undefined_one_year_risk, 'hx_pd': None},
                    'ay_avg': {'call': self.cf_ay_avg, 'hx_pd': None}
                    }

        out = merge_two_dicts({'insurance_id': insurance_id},
                              switcher[insurance_id]['call'](age_insured,
                                                             sex_insured,
                                                             pension_age,
                                                             hx_pd=switcher[insurance_id]['hx_pd'],
                                                             **kwargs))
        return out

    def pv(self, cf, intrest, rounding=False):
        """ Returns present value of cash flows.

        Parameters:
        -----------
        cf: dict {'insurance_id: str, 'payments': series, 'age': int, 'pension_age': int}
        intrest: int, float or series
        """
        cfs = cf['payments']
        insurance_id = cf['insurance_id']
        year = pd.Series(cfs.index)
        self.yield_curve = x_to_series(intrest, len(cfs))

        if insurance_id in ['OPLL', 'NPLL-B', 'ay_avg']:
            pv_factors = self.yield_curve.map(lambda r: 1. / (1 + r / 100.)) ** year
        elif insurance_id in ['NPTL-B', 'NPTL-O']:
            pv_factors = self.yield_curve.map(lambda r: 1. / (1 + r / 100.)) ** (year + 0.5)
        elif insurance_id in ['NPLL-O', 'NPLLRS', 'NPLLRU']:
            nyears_till_pension_age = cf['pension_age'] - cf['age']
            year = year + 0.5 * (year <= nyears_till_pension_age)
            pv_factors = self.yield_curve.map(lambda r: 1. / (1 + r / 100.)) ** year
        else:
            print("---ERROR: cannot process insurance_id: {0}".format(insurance_id))

        present_value = sum(cfs * pv_factors)
        if rounding:
            rounding = self.params['round']
            return round(present_value, rounding)
        else:
            return present_value

    def run_test(self):
        """ Performs tariff calulations on testdata.

        Parameters:
        ----------
        d: dict.
        """
        if self.testdata is None:
            print("No testdata available for table {}".format(self.tablename))
            return None
        msg1, msg2, msg3 = ("Generating cash flows...please wait...",
                            "Calculating present value of cash flows...",
                            "Sum of Errors Squared = ")
        print(msg1)
        testdata = self.testdata
        map_to_cashflows = lambda row: self.cf(insurance_id=row['insurance_id'],
                                               age_insured=row['age'],
                                               sex_insured=row['sex'],
                                               pension_age=row['pension_age'],
                                               intrest=row['intrest'])
        map_to_present_value = lambda row: self.pv(cf=row['cf'], intrest=row['intrest'])

        testdata['cf'] = testdata.apply(map_to_cashflows, axis=1)
        print(msg2)
        testdata['calculated'] = testdata.apply(map_to_present_value, axis=1)
        testdata['difference'] = testdata['test_value'] - testdata['calculated']
        del testdata['cf']
        error_squared = sum(testdata['difference'] * testdata['difference'])
        print(msg3),
        print(error_squared)
        return testdata

    def performance_test(self):
        """ Equal to run_test() but returns output to screen.

        Parameters:
        ----------
        d: dict.
        """

        testdata = self.testdata

        for row in testdata.itertuples():
            cfs = self.cf(row.insurance_id,
                          row.age,
                          row.sex,
                          row.pension_age,
                          intrest=row.intrest)
            calculated = self.pv(cfs, row.intrest)
            print("#{0} -- {1} -- {2}".format(row.Index, row.insurance_id, row.test_value - calculated))

    def calculate_cashflows(self, pension_age, intrest=3):
        """ Returns table with cashflows per insurance_id and age.

        Parameters:
        -----------
        pension_age: int
        intrest: int, float or Series. Default 3 pct.
        """

        # create table layout with all desired tariff combinations
        df = cartesian(lists=[INSURANCE_IDS, [MALE, FEMALE], range(LOWAGE, UPAGE)],
                       colnames=['insurance_id', 'sex_insured', 'age_insured'])

        # generate cashflows
        def map_to_cf(row):
            return self.cf(insurance_id=row['insurance_id'],
                           age_insured=row['age_insured'],
                           sex_insured=row['sex_insured'],
                           pension_age=pension_age,
                           intrest=intrest)

        df['cf'] = df.apply(map_to_cf, axis=1)
        self.intrest = intrest
        self.pension_age = pension_age
        self.cfs = df
        return df

    def calculate_factors(self, intrest, pension_age=67):
        """ Returns factors.

        Parameters:
        -----------
        intrest: int, float or Series.
        pension_age: int. Default 67 year.
        """
        if (intrest == self.intrest) and (pension_age == self.pension_age):
            factors = self.cfs
        else:
            self.cfs = self.calculate_cashflows(intrest=intrest, pension_age=pension_age)
            factors = self.cfs.copy(deep=True)
        factors['tar'] = factors.apply(lambda row: self.pv(row['cf'], intrest=intrest), axis=1)
        factors.set_index(['insurance_id', 'sex_insured', 'age_insured'], inplace=True)
        factors.drop('cf', inplace=True, axis=1)
        self.factors = factors
        return factors

    def export(self, xlswb, intrest, pension_age=67):
        """ Exports results to given xlswb.

        Parameters:
        -----------
        xlswb: str
        intrest: int, float or Series.
        pension_age: int. Default 67 year.
        """
        if (intrest == self.intrest) and (pension_age == self.pension_age):
            result = self.factors
        else:
            result = self.calculate_factors(intrest=intrest, pension_age=pension_age)

        sheets = OrderedDict()
        sheets['legend'] = self.legend
        sheets['factors'] = result.unstack(['sex_insured', 'insurance_id'])
        temp = self.cfs.copy(deep=True)
        temp['cf'] = temp['cf'].map(lambda x: x['payments'])
        cashflows = expand(temp, 'cf')
        cashflows.set_index(['sex_insured', 'insurance_id', 'age_insured', 'year'], inplace=True)
        sheets['cashflows'] = cashflows.unstack(['sex_insured', 'insurance_id'])
        sheets['yield_curve'] = pd.DataFrame(self.yield_curve, columns=['intrest'])
        sheets['lx'] = pd.concat([self.lx_table[MALE], self.lx_table[FEMALE]], axis=1)
        sheets['hx'] = pd.concat([self.hx[MALE], self.hx[FEMALE]], axis=1)
        # TODO : Python 2 verwacht sheetname=sheet
        sheets['adjustments'] = pd.read_excel(self.excel_filepath, sheet_name='tbl_adjustments')

        # write everything to Excel
        writer = pd.ExcelWriter(xlswb)
        for sheet_name, content in sheets.items():
            content.to_excel(writer, sheet_name)
        writer.save()

        msg = "Ready. See {0} for output".format(xlswb)
        print(msg)
