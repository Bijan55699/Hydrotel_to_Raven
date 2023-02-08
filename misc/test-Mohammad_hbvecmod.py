from ravenpy.models.emulators.hbvecmod import HBVECMOD, HBVECMOD_OST
from ravenpy.extractors.routing_product import RoutingProductShapefileExtractor
from ravenpy.models import get_average_annual_runoff

TS = "/home/mohammad/ravenpy/test_hbvecmod_MOhammad/famine_input9.nc"
model = HBVECMOD(workdir="/home/mohammad/ravenpy/test_hbvecmod_MOhammad")

# Model parameters (X01, X02, ...)
default = [1.0, 1.0, 0.21941, 0.15725, 2.65, 0.0, 1.0 , 4.0, 0.0464, 1.0, 1.0, 1.0, 1.0, 0.01, 0.01, 1.0, 0.03,
           0.03, 1.1, 0.02, 100.0, 0.01, 0.01, 0.1, 1.0, 0.1, 0.01]


model.config.rvp.params = HBVECMOD.Params(*default)
model.config.rvt.nc_index = [1,2,3]
# Extract HRUs and Basins from shapefile
extractor = RoutingProductShapefileExtractor(
    "/home/mohammad/Dossier_travail/Raven/SLSO.zip",
    routing_product_version="2.1",
)
rv_objs = extractor.extract()

# Set channel profiles
model.config.rvp.channel_profiles = rv_objs.pop("channel_profiles")

# dumping the rvs to the directory
#model.model_path


# Set HRUs, SubBasins, etc.
for k, v in rv_objs.items():
    model.config.rvh.update(k, v)

# Set gauged subbasins
# gauged_sb_ids = [159, 160]
gauged_sb_ids = [160]

for sb in model.config.rvh.subbasins:
    # Will set `gauged` to True|False, depending on whether the ID is in the list
    sb.gauged = sb.subbasin_id in gauged_sb_ids

# Compute total HRU area [km^2]
area = sum([hru.area for hru in model.config.rvh.hrus])

# Compute annual runoff
model.config.rvp.avg_annual_runoff = get_average_annual_runoff(
    TS, area * 1e6, obs_var="qobs"
)

# model.config.rvi.configure_from_nc_data([TS])
model.config.rvi.duration = 365

# Run the model
model(ts=[TS], overwrite=True)
model.hydrograph.q_obs


from matplotlib import pyplot as plt
model.q_sim.isel(nbasins=0).plot(label="sim")
model.hydrograph.q_obs.isel(nbasins=0).plot(label="obs")
plt.legend()
plt.show()
