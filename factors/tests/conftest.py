import shutil
import tempfile

import os
import pytest

from factors import LifeTable


@pytest.yield_fixture(autouse=True)
def guaranteed_temp_folder_for_each_test():
    """Make sure that each test runs in a temporary directory."""
    cwd = os.getcwd()  # store the current working directory
    temp_dir = tempfile.mkdtemp()  # create a temp dir
    os.chdir(temp_dir)  # cd into the temp dir
    yield  # let the test run

    os.chdir(cwd)  # cd back into the original working directory
    shutil.rmtree(temp_dir)  # destroy the temp dir


@pytest.fixture(scope="session")
def aegon_table():
    return LifeTable("AEG2011")


@pytest.fixture(scope="session")
def ag_table():
    return LifeTable("AG2014")
