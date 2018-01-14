import os

import pytest

from factors.utils import get_excel_filepath


def test_get_xlswb():
    tablename = "AEG2011"
    excel_filepath = get_excel_filepath(tablename)
    assert "{tablename}.xlsx".format(tablename=tablename) in excel_filepath
    assert os.path.isfile(excel_filepath)
    # It will raise a ValueError if the excel sheet doesn't exists
    with pytest.raises(ValueError):
        get_excel_filepath("AEG")
