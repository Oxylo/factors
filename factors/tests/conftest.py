import os

import pytest

from factors import LifeTable


@pytest.fixture
def aegon_table():
    tables = LifeTable("AEG2011")
    return tables
