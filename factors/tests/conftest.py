import pytest

from factors import LifeTable


@pytest.fixture
def aegon_table():
    return LifeTable("AEG2011")


@pytest.fixture
def ag_table():
    return LifeTable("AG2014")
