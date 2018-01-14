from factors import LifeTable


def test_data():
    tables = LifeTable("AEG2011")
    testdata = tables.run_test()
    assert testdata is not None
    error_squared = sum(testdata['difference'] * testdata['difference'])
    assert error_squared < 3.5e-5
