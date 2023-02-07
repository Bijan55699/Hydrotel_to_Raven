
"""
Created on Wed Dec  7 14:57:03 2022

@author: Mohammad Biozhanimanzar, Ouranos
mohbiz1@ouranos.ca
"""

import numpy as np
import os
import xarray as xr
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# %% Section 1: Read inputs

# This is the HBVECMOD
name = 'HBVSIMHAR'  #This is HBVECMOD emulator
pth_base = '/home/mohammad/Dossier_travail/Hydrotel/Uncertainity'
pth = os.path.join(pth_base,name,'sim/exec/model/p00/output/run-0_Hydrographs.nc')
data = (xr.open_dataset(pth,mode = 'r')).expand_dims(model=[name])
data = data.sel(time=slice('2000-01-01', '2019-12-31'))


dqmax_hbvec = (((data.q_sim.resample(time='AS').max(skipna = False)) - (data.q_obs.resample(time='AS').max(skipna = False)))/((data.q_sim.resample(time='AS').max(skipna = False))))*100
dqmax_hbvec.name = 'qmax'
def doymax(grp):
    i = grp.argmax('time')
    return grp.time.dt.dayofyear.isel(time=i, drop=True)
daymax_hbvec = data.q_sim.resample(time='AS').map(doymax)
daymax_hbvec.name = 'day_qmax'
df = dqmax_hbvec.to_dataframe(name = name)

realizations = ["DEGSIMHAM","DEGSIMHAR","DEGSIMOUD","DEGSIMMOH",
                "DEGHBVHAM","DEGHBVHAR","DEGHBVOUD","DEGHBVMOH",
                "DEGHMEHAM","DEGHMEHAR","DEGHMEOUD","DEGHMEMOH",
                "HBVSIMHAM","HBVSIMHAR","HBVSIMOUD","HBVSIMMOH",
                "HBVHBVHAM","HBVHBVHAR","HBVHBVOUD","HBVHBVMOH",
                "HBVHMEHAM","HBVHMEHAR","HBVHMEOUD","HBVHMEMOH",
                "ROSSIMHAM","ROSSIMHAR","ROSSIMOUD","ROSSIMMOH",
                "ROSHBVHAM","ROSHBVHAR","ROSHBVOUD","ROSHBVMOH",
                "ROSHMEHAM","ROSHMEHAR","ROSHMEOUD","ROSHMEMOH",
                "HMESIMHAM","HMESIMHAR","HMESIMOUD","HMESIMMOH",
                "HMEHBVHAM","HMEHBVHAR","HMEHBVOUD","HMEHBVMOH",
                "HMEHMEHAM","HMEHMEHAR","HMEHMEOUD","HMEHMEMOH"]  
dqmax_merged = dqmax_hbvec
daymax_hbvec_merged = daymax_hbvec
for i in range(len(realizations)-1):
    name = realizations[i]
    if name =="HBVSIMHAR":
        continue
    else:
        pth = os.path.join(pth_base,name,'sim/exec/model/p00/output/run-0_Hydrographs.nc')
        data = (xr.open_dataset(pth,mode = 'r')).expand_dims(model=[name])
        data = data.sel(time=slice('2000-01-01', '2019-12-31'))
        dqmax_iter = (((data.q_sim.resample(time='AS').max(skipna = False)) - (data.q_obs.resample(time='AS').max(skipna = False)))/((data.q_sim.resample(time='AS').max(skipna = False))))*100
        dqmax_iter.name = 'qmax'
        dqmax_merged = xr.merge([dqmax_merged,dqmax_iter])
        daymax_iter = data.q_sim.resample(time='AS').map(doymax)
        daymax_iter.name = 'day_qmax'
        xr.merge([daymax_hbvec_merged,daymax_iter])
        


Snowmelt_models = ((dqmax_merged.qmax.sel(model = ['DEGSIMHAR','HBVSIMHAR','ROSSIMHAR','HMESIMHAR'])).to_dataframe()).reset_index(level = [0,1,2]).drop(['time','nbasins','model'],axis=1)  #4 models #(model,time,basin_name)
Snowbalance_models = ((dqmax_merged.qmax.sel(model = ['HBVSIMHAR','HBVHBVHAR','HBVHMEHAR'])).to_dataframe()).reset_index(level = [0,1,2]).drop(['time','nbasins','model'],axis=1) #3 models #(model,time,basin_name)
PET_models = ((dqmax_merged.qmax.sel(model = ['HBVSIMHAM','HBVSIMHAR','HBVSIMOUD','HBVSIMMOH'])).to_dataframe()).reset_index(level = [0,1,2]).drop(['time','nbasins','model'],axis=1) #4 models #(model,time,basin_name)
HBVECMOD = ((dqmax_merged.qmax.sel(model = ['HBVSIMHAR'])).to_dataframe()).reset_index(level = [0,1,2]).drop(['time','nbasins','model'],axis=1) # HBVECMOD model #(model,time,basin_name)

Snowmelt_models['model'] = 'SM'
Snowbalance_models['model'] = 'SB'
PET_models['model'] = 'PET'
HBVECMOD['model'] = 'HBVECMOD'

models = pd.concat([Snowmelt_models,Snowbalance_models,PET_models,HBVECMOD],axis=0,sort=False)
models.replace([np.inf, -np.inf], np.nan, inplace=True)
models = models.dropna()


#Now Plot!
def patch_violinplot(palette, n):
    from matplotlib.collections import PolyCollection
    ax = plt.gca()
    violins = [art for art in ax.get_children() if isinstance(art, PolyCollection)]
    colors = sns.color_palette(palette, n_colors=n) * (len(violins)//n)
    for i in range(len(violins)):
        violins[i].set_edgecolor(colors[i])
              
              
fig,ax = plt.subplots(1,1,sharex = True, figsize = (20,10), dpi = 300)
sns.violinplot(x="basin_name", y="qmax",
            hue="model",
            data=models)
num_cols = models['model'].nunique()
patch_violinplot("bright", num_cols)

plt.grid('on', which='major')
plt.legend(loc="lower left", ncol=4)
plt.xticks(rotation=90)
sns.despine(offset=10, trim=True)
ax.set_ylabel(r'$\Delta$Qmax$(m^3/s)$')
ax.set_xlabel(r'$Subbasins$')
plt.savefig('/home/mohammad/Dossier_travail/Hydrotel/Uncertainity/DeltaQmax.png', dpi=300)













