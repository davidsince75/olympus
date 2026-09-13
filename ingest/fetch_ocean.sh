#!/bin/sh
# Olympus — fetch the two measured sources of the ocean circulation plane.
# Neither needs an account. Both are CC BY 4.0. Run from the project root.
set -e
mkdir -p data

# NOAA Global Drifter Program near-surface velocity climatology, 1/4 deg,
# drogued at 15 m. Laurindo, Mariano & Lumpkin (2017), doi:10.1016/j.dsr.2017.04.009
curl -fSL -o data/gdp_annual.nc \
  "https://erddap.aoml.noaa.gov/gdp/erddap/griddap/drifter_annualmeans.nc?U%5B(-179.875):1:(179.875)%5D%5B(-72.875):1:(84.875)%5D,V%5B(-179.875):1:(179.875)%5D%5B(-72.875):1:(84.875)%5D,N%5B(-179.875):1:(179.875)%5D%5B(-72.875):1:(84.875)%5D"

# Sea-surface temperature from the same drifters, for the temperature colouring.
[ -s data/gdp_sst.nc ] || curl -fSL -o data/gdp_sst.nc \
  "https://erddap.aoml.noaa.gov/gdp/erddap/griddap/drifter_annualmeans.nc?SST%5B(-179.875):1:(179.875)%5D%5B(-72.875):1:(84.875)%5D"

# The same climatology by climatological month, for the seasonal layer. The
# ClimatologicalMonth axis is 0-indexed: 0 is January, 11 is December.
for i in 0 1 2 3 4 5 6 7 8 9 10 11; do
  f=$(printf "data/gdp_i%02d.nc" "$i")
  [ -s "$f" ] || curl -fSL -o "$f" \
    "https://erddap.aoml.noaa.gov/gdp/erddap/griddap/drifter_monthlymeans.nc?U%5B($i):1:($i)%5D%5B(-179.875):1:(179.875)%5D%5B(-72.875):1:(84.875)%5D,V%5B($i):1:($i)%5D%5B(-179.875):1:(179.875)%5D%5B(-72.875):1:(84.875)%5D"
done

# Altimetry-derived ACC fronts from the CNES-CLS18 mean dynamic topography.
# Park & Durand (2019), SEANOE, doi:10.17882/59800
curl -fSL -o data/parkfronts.nc "https://www.seanoe.org/data/00486/59800/data/62985.nc"

ls -l data/gdp_annual.nc data/gdp_sst.nc data/gdp_i*.nc data/parkfronts.nc
