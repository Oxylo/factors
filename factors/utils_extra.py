import pandas as pd
import numpy as np
import settings

# AG2014 characteristics
STARTYEAR = 2014
MAXAGE = 120


def read_generation_table(xlswb, sheetname, calc_year):
    """ Return generations tables (M, F), starting from calculation year
    """
    tables = {}
    data = pd.read_excel(xlswb, skiprows=0, sheetname=sheetname)
    for gender in [settings.MALE, settings.FEMALE]:
        tab = data[data['gender'] == gender]
        tab = tab.iloc[:, 1:]
        tab.set_index('x', inplace=True)
        years_to_skip = calc_year - STARTYEAR
        if years_to_skip < 0:
            print("***ERROR: calculation year should be >= {}".format(STARTYEAR))
            exit()
        else:
            tables[gender] = tab.iloc[:, years_to_skip:]
    return tables


def diagonals_to_columns(df):
    """ Return df with lower triangle diagonals converted to columns.
    """
    frames = []
    nrows = MAXAGE + 1
    for age in range(0, nrows):
        diag = np.diagonal(df, offset=-age)
        index = range(age, nrows)
        ddf = pd.DataFrame(data=diag, index=index, columns=[age])
        frames.append(ddf)
    out = pd.concat(frames, axis=1)
    return out


def qx_to_npx(df):
    """ Return df with qx converted to npx.
    """
    df = 1 - df
    out = df.cumprod().shift()
    for i in df.index:
        out.loc[i, i] = 1
    return out


def stack_columns(df):
    """ Stack columns of given df.
    """
    out = df.T.stack()
    out.index.rename(names=['current', 'age'], inplace=True)
    return pd.DataFrame(out, columns=['lx'])


def flatten_generation_table(data):
    """ Convert 2 dimensional qx table to 1 dimensional lx
    """
    lx_tables = {}
    for gender in [settings.MALE, settings.FEMALE]:
        df = diagonals_to_columns(data[gender])
        df = qx_to_npx(df)
        df.fillna(1, inplace=True)
        lx_tables[gender] = stack_columns(df)
    return lx_tables


def get_lx(lx_tables, current_age):
    """ Return lx_table for given current age
    """
    return {gender: lx_tables[gender].ix[current_age] for gender in [settings.MALE, settings.FEMALE]}


if __name__ == "__main__":
    # user input
    xlswb = settings.XLSWB
    sheetname = "AG2014"
    calc_year = 2017

    data = read_generation_table(xlswb, sheetname, calc_year)
    lx = flatten_generation_table(data)
    print(lx)
