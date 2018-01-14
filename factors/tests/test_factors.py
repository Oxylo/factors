import os
from factors import LifeTable, NewLifeTable


def test_data():
    tables = LifeTable("AEG2011")
    testdata = tables.run_test()
    assert testdata is not None
    error_squared = sum(testdata['difference'] * testdata['difference'])
    assert error_squared < 3.5e-5


def test_data_new_lifetable():
    xlswb = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "AEG2011.xlsx")
    tables = NewLifeTable("AEG2011", xlswb=xlswb)
    testdata = tables.run_test()
    assert testdata is not None
    error_squared = sum(testdata['difference'] * testdata['difference'])
    assert error_squared < 3.5e-5


def test_single_person():
    tables = LifeTable("AEG2011")
    test_value = 5.0849
    params = dict(
        sex_insured="M",
        age_insured=15,
        insurance_id="OPLL",
        intrest=1.867,
        pension_age=70,

    )
    cf_OP = tables.cf_retirement_pension(**params)
    factor_OP = tables.pv(
        dict(
            insurance_id=params["insurance_id"],
            payments=cf_OP["payments"],
            age=params["age_insured"],
            pension_age=params["pension_age"],

        ),
        intrest=params["intrest"]
    )
    assert factor_OP == test_value


def test_single_person_new():
    xlswb = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "AEG2011.xlsx")
    tables = NewLifeTable("AEG2011", xlswb=xlswb)
    test_value = 5.0849
    params = dict(
        sex_insured="M",
        age_insured=15,
        insurance_id="OPLL",
        intrest=1.867,
        pension_age=70,

    )
    cf_OP = tables.cf_retirement_pension(**params)
    factor_OP = tables.pv(
        dict(
            insurance_id=params["insurance_id"],
            payments=cf_OP["payments"],
            age=params["age_insured"],
            pension_age=params["pension_age"],

        ),
        intrest=params["intrest"]
    )
    assert factor_OP == test_value