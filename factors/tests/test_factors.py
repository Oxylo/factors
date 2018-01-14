def test_data(aegon_table):
    tables = aegon_table
    testdata = tables.run_test()
    assert testdata is not None
    error_squared = sum(testdata['difference'] * testdata['difference'])
    assert error_squared < 3.5e-5


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
