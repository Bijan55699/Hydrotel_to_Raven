
"""
Created on Wed Dec  7 14:57:03 2022

@author: Mohammad Biozhanimanzar, Ouranos
mohbiz1@ouranos.ca
"""


import netCDF4 as nc
import numpy as np
import os



# %% Section 1: Read inputs

# inputs: 
name = 'DEGSIMOUD'
pth_base = '/home/mohammad/Dossier_travail/Hydrotel/Uncertainity'
pth = os.path.join(pth_base,name,'sim/exec/model/p00/output/run-0_Hydrographs.nc')

data = nc.Dataset(pth,mode = 'r')


data_Q = pd.read_excel(pth, index_col = None)

st = {'Yamaska':'MONT00003', 'Richelieu':'MONT00502', 'Saint_Jacques':'MONT01296', 'Saint_Regis':'MONT01317', 'Chateauguay':'MONT01335', 'Maskinonge':'SLNO00496', 'Assomption':'SLNO00563', 'du_Loup':'SLNO00847', 'Saint_Maurice':'SLNO00930',
      'Batiscan':'SLNO02927', 'Becancour':'SLSO00767', 'Nicolet':'SLSO00941', 'Saint_Francois':'SLSO01193'}  

idd = st[name]
Q = pd.DataFrame({'Q(m3/s)':data_Q[idd][0:],
                   'Date':data_Q['Date'][0:].astype('datetime64[ns]')})

# Transform the Date to year, month, and day columns
Q['year'] = pd.DatetimeIndex(Q['Date']).year
Q['month'] = pd.DatetimeIndex(Q['Date']).month
Q['day'] = pd.DatetimeIndex(Q['Date']).day

# Calculating the annual maxima

Q_annual_max = Q.loc[Q.groupby("year")["Q(m3/s)"].idxmax()]
Q_annual_max.reset_index(inplace=True) 

