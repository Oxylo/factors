import pandas as pd
import pytest
from factors.models import LifeTable
from factors.settings import MALE, FEMALE


@pytest.fixture
def my_lifetable(tablename):
    """ Returns a Lifetable instance
    """
    return LifeTable(tablename)


# ------ test npx ----------------------------------------------------
params = "tablename, age, sex, nyears, test_value"


@pytest.mark.parametrize(params, [
    ("AEG2011", 25, MALE, 40, 0.962021849),
    ("AEG2011", 50, FEMALE, 30, 0.822403907),
    ("AEG2011", 75, MALE, 20, 0.152371044),
    ("AEG2011", 100, FEMALE, 10, 0.001699115),
    ])
def test_npx(tablename, age, sex, nyears, test_value):
    tab = my_lifetable(tablename)
    calculated = tab.npx(age, sex, nyears)
    assert (calculated == pytest.approx(test_value))


# ------ test qx -----------------------------------------------------
params = "tablename, age, sex, test_value"


@pytest.mark.parametrize(params, [
    ("AEG2011", 25, MALE, 0.000080794352),
    ("AEG2011", 50, FEMALE, 0.001374618403),
    ("AEG2011", 75, MALE, 0.013947512240),
    ("AEG2011", 100, FEMALE, 0.341802517430),
    ])
def test_qx(tablename, age, sex, test_value):
    tab = my_lifetable(tablename)
    calculated = tab.qx(age, sex)
    assert (calculated == pytest.approx(test_value))


# ------ test nqx -----------------------------------------------------
params = "tablename, age, sex, nyears, test_value"


@pytest.mark.parametrize(params, [
    ("AEG2011", 25, MALE, 40, 0.003585687),
    ("AEG2011", 50, FEMALE, 30, 0.017858528),
    ("AEG2011", 75, MALE, 20, 0.050825338),
    ("AEG2011", 100, FEMALE, 10, 0.002328259),
    ])
def test_nqx(tablename, age, sex, nyears, test_value):
    tab = my_lifetable(tablename)
    calculated = tab.nqx(age, sex, nyears)
    assert (calculated == pytest.approx(test_value))


# ------ test cf_annuity ----------------------------------------------
params = "tablename, age_insured, sex_insured, year_cf, test_value"


@pytest.mark.parametrize(params, [
    ("AEG2011", 27, MALE, 3, 0.999690687),
    ("AEG2011", 35, MALE, 18, 0.990939192),
    ("AEG2011", 24, FEMALE, 7, 0.999479725),
    ("AEG2011", 42, FEMALE, 20, 0.963696859),
    ])
def test_cf_annuity(tablename, age_insured, sex_insured,
                    year_cf, test_value):
    tab = my_lifetable(tablename)
    # table_insured = table.get_lx_table()[sex_insured]
    # if you want to make it work for generation tables too:
    table_insured = tab.lx(age_insured)[sex_insured]['lx']
    calculated = tab.cf_annuity(age_insured, table_insured, defer=0)
    assert (calculated[year_cf] == pytest.approx(test_value))


# ------ cf_ay_avg ----------------------------------------------------
params = "tablename, age_insured, sex_insured, year_cf, test_value"


@pytest.mark.parametrize(params, [
    ("AEG2011", 60, MALE, 5, 0.982123937),
    ("AEG2011", 62, MALE, 8, 0.964624171),
    ("AEG2011", 64, MALE, 11, 0.940364275),
    ("AEG2011", 66, MALE, 14, 0.896005977),
    ])
def test_cf_ay_avg(tablename, age_insured, sex_insured,
                    year_cf, test_value):
    tab = my_lifetable(tablename)
    calculated = tab.cf_ay_avg(age_insured, sex_insured)
    assert (calculated['payments'][year_cf] == pytest.approx(test_value))


# ------ test ay_avg --------------------------------------------------
params = "tablename, age_insured, sex_insured, intrest, rounding, test_value"


@pytest.mark.parametrize(params, [
    ("AEG2011", 60, MALE, 3.0, True, 19.5641),
    ("AEG2011", 62, MALE, 3.0, True, 18.8209),
    ("AEG2011", 64, MALE, 3.0, True, 18.0491),
    ("AEG2011", 66, MALE, 3.0, True, 17.2433),
    ])
def test_ay_avg(tablename, age_insured, sex_insured,
                intrest, rounding, test_value):
    tab = my_lifetable(tablename)
    calculated = tab.ay_avg(age_insured, sex_insured, intrest,
                            rounding=rounding)
    assert (calculated == pytest.approx(test_value))


# ------ test create_lookup_table -------------------------------------
params = "tablename, intrest, sex_insured, age_insured, test_value"


@pytest.mark.parametrize(params, [
    ("AEG2011", 3.0, MALE, 60, 18.0889918),
    ("AEG2011", 3.0, MALE, 62, 17.4017847),
    ("AEG2011", 3.0, MALE, 64, 16.6882039),
    ("AEG2011", 3.0, MALE, 66, 15.9431797),
    ])
def test_create_lookup_table(tablename, intrest, sex_insured,
                             age_insured, test_value):
    tab = my_lifetable(tablename)
    calculated = tab.create_lookup_table(intrest)
    assert (calculated.loc[sex_insured].loc[age_insured]['cf'] ==
            pytest.approx(test_value))


# ------ test cf_retirement_pension -----------------------------------
params = ("tablename, age_insured, sex_insured, "
          "pension_age, year_cf, test_value")


@pytest.mark.parametrize(params, [
    ("AEG2011", 15, MALE, 67, 51, 0.000000000),
    ("AEG2011", 15, MALE, 67, 52, 0.476719925),
    ("AEG2011", 15, MALE, 67, 75, 0.402503394),
    ("AEG2011", 15, MALE, 67, 76, 0.345734524),
    ])
def test_cf_retirement_pension(tablename, age_insured, sex_insured,
                               pension_age, year_cf, test_value):
    tab = my_lifetable(tablename)
    calculated = tab.cf_retirement_pension(age_insured, sex_insured,
                                           pension_age)
    assert (calculated['payments'][year_cf] ==
            pytest.approx(test_value))


# ------ test cf_defined_partner -----------------------------------
params = ("tablename, age_insured, sex_insured, "
          "pension_age, year_cf, test_value")


@pytest.mark.parametrize(params, [
    ("AEG2011", 15, MALE, 67, 25, 0.00438843),
    ("AEG2011", 15, MALE, 67, 26, 0.00485197),
    ("AEG2011", 15, MALE, 67, 51, 0.06571732),
    ("AEG2011", 15, MALE, 67, 52, 0.07226776),
    ("AEG2011", 15, MALE, 67, 75, 0.37404980),
    ("AEG2011", 15, MALE, 67, 76, 0.37938236),
    ])
def test_cf_defined_partner(tablename, age_insured, sex_insured,
                            pension_age, year_cf, test_value):
    tab = my_lifetable(tablename)
    calculated = tab.cf_defined_partner(age_insured, sex_insured,
                                        pension_age)
    assert (calculated['payments'][year_cf] ==
            pytest.approx(test_value))


# ------ test cf_undefined_partner ------TODO: komt deze test nog niet door!**

params = ("tablename, age_insured, sex_insured, "
          "pension_age, intrest, hx_pd, year_cf, test_value")


@pytest.mark.parametrize(params, [
    ("AEG2011", 60, MALE, 67, 3.0, 'one', 20, 0.162132918),
    ("AEG2011", 60, MALE, 67, 3.0, 'one', 40, 0.133635078),
    ("AEG2011", 60, MALE, 67, 3.0, 'one', 51, 0.000440754),
    ("AEG2011", 60, MALE, 67, 3.0, 'ukv', 20, 0.157276446),
    ("AEG2011", 60, MALE, 67, 3.0, 'ukv', 40, 0.128830446),
    ("AEG2011", 60, MALE, 67, 3.0, 'ukv', 51, 0.000424816),
    ])
def test_cf_undefined_partner(tablename, age_insured, sex_insured,
                              pension_age, intrest, hx_pd,
                              year_cf, test_value):
    tab = my_lifetable(tablename)
    calculated = tab.cf_undefined_partner(age_insured, sex_insured,
                                          pension_age, intrest=intrest,
                                          hx_pd=hx_pd)
    assert (calculated['payments'][year_cf] ==
            pytest.approx(test_value))

# ------ test cf_defined_one_year_risk ------------------*** TODO *** -

# ------ test cf_undefined_one_year_risk ----------------*** TODO ***


# ------ test cf --------------------------------------*** TODO: 2/4 **

params = ("tablename, insurance_id, age_insured, sex_insured, "
          "pension_age, intrest, year_cf, test_value")


@pytest.mark.parametrize(params, [
    ("AEG2011", 'OPLL', 15, MALE, 67, None, 52, 0.476719925),
    ("AEG2011", 'NPLL-B', 15, MALE, 67, None, 51, 0.06571732),
    ("AEG2011", 'NPLLRS', 60, MALE, 67, 3.0, 40, 0.133635078),
    ("AEG2011", 'NPLLRU', 60, MALE, 67, 3.0, 40, 0.128830446),
    ])
def test_cf2(tablename, insurance_id, age_insured, sex_insured,
             pension_age, intrest, year_cf, test_value):
    tab = my_lifetable(tablename)
    calculated = tab.cf(insurance_id, age_insured, sex_insured,
                        pension_age, intrest=intrest)
    assert (calculated['payments'][year_cf] ==
            pytest.approx(test_value))

# ------ test pv -----------------------------------------------------


params = "tablename, cfs, intrest, rounding, test_value"


@pytest.mark.parametrize(params, [
    ("AEG2011", {'insurance_id': 'OPLL',
                 'payments': pd.Series([100, -10, 500, -200]),
                 'age': None,
                 'pension_age': None}, 3, False, 378.5608848322),
    ("AEG2011", {'insurance_id': 'OPLL',
                 'payments': pd.Series([100, -10, 500, -200]),
                 'age': None,
                 'pension_age': None}, 5, False, 371.2234099989),
    ("AEG2011", {'insurance_id': 'OPLL',
                 'payments': pd.Series([100, -10, 500, -200]),
                 'age': None,
                 'pension_age': None}, 3, True, 378.5609),
    ("AEG2011", {'insurance_id': 'OPLL',
                 'payments': pd.Series([100, -10, 500, -200]),
                 'age': None,
                 'pension_age': None}, 5, True, 371.2234),
    ])
def test_pv(tablename, cfs, intrest, rounding, test_value):
    tab = my_lifetable(tablename)
    calculated = tab.pv(cfs, intrest, rounding=rounding)
    assert (calculated == pytest.approx(test_value))

