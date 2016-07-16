import os

LOWAGE = 15
UPAGE = 70
MAXAGE = 120

DATADIR = '/home/pieter/projects/factors/data'
INFILE = 'lifedb.xls'

XLSWB = os.path.join(DATADIR, INFILE)

INSURANCE_IDS = ['OPLL', 'NPLL-B', 'NPLL-O',
                 'NPLLRS', 'NPTL-B', 'NPTL-O', 'ay_avg']
