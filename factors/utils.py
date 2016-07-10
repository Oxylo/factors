import pandas as pd
import itertools


def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy.
    http://stackoverflow.com/questions/38987/how-can-i-merge-two-python-dictionaries-in-a-single-expression
    """
    z = x.copy()
    z.update(y)
    return z


def dictify(frame):
    """ Converts multi-indexed dataframe to nested dict.
    http://stackoverflow.com/questions/19798112/convert-pandas-dataframe-to-a-nested-dict
    """
    if len(frame.columns) == 1:
        if frame.values.size == 1:
            return frame.values[0][0]
        return frame.values.squeeze()
    grouped = frame.groupby(frame.columns[0])
    d = {k: dictify(g.ix[:, 1:]) for k, g in grouped}
    return d


def to_excel(frame, xlswb='output.xlsx'):
    """ Export frame to Excel.

    Parameters
    ----------
    frame: DataFrame to export
    xlswb: Excel file name
    """
    writer = pd.ExcelWriter(xlswb)
    frame.to_excel(writer, 'Sheet1')
    writer.save()
    return 0


def prae_to_continuous(cfs):
    """ Converts preanumerando to continuous cashflows.

    Parameters
    ----------
    cfs: Series with cashflows.
    """

    first_cf_index = cfs[cfs > 0].index[0]
    cf_postnumerando = cfs.copy()
    cf_postnumerando[first_cf_index] = 0
    cf_average = (cfs + cf_postnumerando) / 2.
    return cf_average


def expand(df, column_to_expand):
    """ Returns df with 1 column having multiple values
    expanded to single value cells.

    Parameters:
    ----------
    df: DataFrame
    column_to_expand: str
    """
    colnames = list(df.columns)
    colnames.remove(column_to_expand)
    df.set_index(colnames, inplace=True)
    expanded = df.apply(lambda row: row[column_to_expand], axis=1).stack()
    expanded = expanded.reset_index()
    expanded.columns = colnames + ['year'] + [column_to_expand]
    return expanded


def cartesian(lists, colnames):
    """
    Returns a DataFrame with the Cartesian product of given lists.

    Parameters:
    -----------
    lists: list of lists
    colnames: list of strings
    """
    df = pd.DataFrame.from_records(list(itertools.product(*lists)),
                                   columns=colnames)
    return df
