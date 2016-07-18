import os


LOWAGE = 15
UPAGE = 70
MAXAGE = 120

DATADIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
INFILE = 'lifedb.xls'

XLSWB = os.path.join(DATADIR, INFILE)

INSURANCE_IDS = ['OPLL', 'NPLL-B', 'NPLL-O',
                 'NPLLRS', 'NPTL-B', 'NPTL-O', 'ay_avg']
