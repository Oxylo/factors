import os
import numpy as np


def test_ag2014_data(ag_table):
    tables = ag_table
    testdata = tables.run_test()
    assert testdata is not None
    error_squared = np.sum(testdata['difference'] * testdata['difference'])
    assert error_squared < 3.5


def test_aeg2011_data(aegon_table):
    tables = aegon_table
    testdata = tables.run_test()
    assert testdata is not None
    error_squared = sum(testdata['difference'] * testdata['difference'])
    assert error_squared < 3.5e-5


def test_export(aegon_table):
    tables = aegon_table
    tables.export("text.xlsx", intrest=3, pension_age=67)
    assert os.path.exists("text.xlsx")
    # TODO Load Excel sheet and check that it's correct


def test_single_person(aegon_table):
    tables = aegon_table
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
