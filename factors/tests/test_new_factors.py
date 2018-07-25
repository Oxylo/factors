import pytest
from factors.models import LifeTable
from factors.settings import MALE, FEMALE


@pytest.fixture
def my_lifetable(tablename):
    """ Returns a Lifetable instance
    """
    return LifeTable(tablename)


params = "tablename,age_insured,sex_insured,year_cf,test_result"


@pytest.mark.parametrize(params, [
    ("AEG2011", 27, MALE, 3, 0.999690687),
    ("AEG2011", 35, MALE, 18, 0.990939192),
    ("AEG2011", 24, FEMALE, 7, 0.999479725),
    ("AEG2011", 42, FEMALE, 20, 0.963696859),
    ])
def test_cf_annuity(tablename, age_insured, sex_insured,
                    year_cf, test_result):
    tab = my_lifetable(tablename)
    # table_insured = table.get_lx_table()[sex_insured]
    # if you want to make it work for generation tables too:
    table_insured = tab.lx(age_insured)[sex_insured]['lx']
    calculated = tab.cf_annuity(age_insured, table_insured, defer=0)
    assert (calculated[year_cf] == pytest.approx(test_result))
