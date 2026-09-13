"""
Olympus — the schematic deep register.

Every path below is ILLUSTRATION. What is not illustration is the set of
gateways each path is made to pass through: sills, fracture zones, channels
and formation sites at their published positions and depths. Those are listed
in NODES with a citation each, and the artifact renders them as measured
points on an explicitly schematic line.

Depth is metres, positive down, given per control vertex. It drives the radial
position inside the globe, at the vertical exaggeration named in ocean_common.
"""

# --- gateways, at their true positions; depth = published sill or core depth ---
NODES = [
 # id                 lon      lat    depth   label                                  kind      cite
 ("denmark",        -27.0,   66.0,    620, "Denmark Strait sill",                   "sill",
     "Sill ~620 m. Overflow 3.20 +/- 0.50 Sv, 1996-2015. Jochumsen et al. (2017), JGR Oceans, doi:10.1002/2017JC012803"),
 ("faroe",           -8.2,   61.4,    840, "Faroe Bank Channel sill",               "sill",
     "Sill 840 m, width ~15 km. Overflow 2.1 +/- 0.2 Sv. Osterhus et al. (2008)"),
 ("cgfz",           -34.5,   52.5,   3500, "Charlie-Gibbs Fracture Zone",           "gate",
     "The passage by which Iceland-Scotland overflow water crosses the Mid-Atlantic Ridge into the western basin."),
 ("vema",           -39.3,  -31.2,   4650, "Vema Channel",                          "gate",
     "Sill ~4650 m. The principal gateway for Antarctic Bottom Water entering the Brazil Basin."),
 ("romanche",       -18.0,    0.0,   4350, "Romanche Fracture Zone",                "gate",
     "The deepest breach of the Mid-Atlantic Ridge at the equator; carries bottom water into the eastern Atlantic."),
 ("drake_deep",     -60.0,  -58.0,   3400, "Drake Passage",                         "gate",
     "ACC transport 173.3 +/- 10.7 Sv, 2007-2011, moored array. Donohue et al. (2016), GRL, doi:10.1002/2016GL070319"),
]

# --- the limbs. control vertices are [lon, lat, depth_m] ---
# The warm upper limb: the half of the conveyor that goes north. It is the
# reason the whole thing matters -- roughly a petawatt of heat carried into the
# North Atlantic -- and leaving it undrawn left the globe showing only the
# return. The surface field measures this water; this line says which water it
# is and where it is going.
WARM = [
 ("warm_main", "Warm upper limb -> Nordic Seas", "warm", [
    [105.0, -12.0, 120], [88.0, -17.0, 130], [70.0, -25.0, 140], [55.0, -33.0, 150],
    [40.0, -37.0, 160], [30.0, -38.0, 170], [22.0, -37.0, 160], [12.0, -33.0, 140],
    [2.0, -26.0, 120], [-8.0, -20.0, 110], [-20.0, -14.0, 100], [-30.0, -9.0, 95],
    [-36.0, -3.0, 90], [-42.0, 2.0, 90], [-48.0, 5.0, 90], [-54.0, 8.0, 95],
    [-62.0, 12.0, 100], [-70.0, 14.5, 100], [-77.0, 15.5, 100], [-84.0, 18.5, 110],
    [-85.5, 21.5, 110], [-84.0, 23.5, 110], [-81.0, 23.5, 105], [-79.8, 26.0, 105],
    [-79.3, 29.0, 120], [-76.5, 32.5, 140], [-72.0, 36.5, 160], [-64.0, 39.5, 200], [-54.0, 41.5, 240], [-44.0, 44.5, 270],
    [-34.0, 48.5, 290], [-24.0, 52.5, 300], [-16.0, 56.5, 300], [-10.0, 61.0, 290],
    [-5.0, 65.0, 270], [-2.0, 69.0, 240], [-4.0, 72.0, 200]]),
 ("warm_lab",  "Warm upper limb -> Irminger and Labrador seas", "warm", [
    [-24.0, 52.5, 300], [-28.0, 55.5, 300], [-33.0, 58.0, 290], [-38.5, 59.0, 280],
    [-44.5, 58.5, 270], [-50.0, 57.5, 260], [-55.0, 57.5, 250]]),
]

# Deep western boundary current, Nordic overflows -> South Atlantic.
NADW = [
 ("nadw_dsow", "Denmark Strait overflow -> DWBC", "nadw", [
    [-8.0, 68.0, 400], [-19.0, 67.5, 500], [-27.0, 66.0, 620], [-31.0, 64.5, 1400],
    [-34.0, 62.5, 2100], [-40.0, 60.5, 2600], [-44.0, 59.0, 2900], [-49.0, 58.0, 3000],
    [-52.5, 56.5, 3000], [-51.0, 52.5, 2900], [-48.5, 47.5, 2900], [-46.5, 43.0, 3000],
    [-57.0, 39.0, 3200], [-68.0, 36.0, 3400], [-74.0, 33.0, 3500], [-77.0, 29.0, 3600],
    [-76.0, 25.0, 3700], [-70.5, 21.5, 3700], [-64.0, 19.6, 3800], [-57.5, 13.0, 3800],
    [-48.0, 4.5, 3800], [-40.0, 0.5, 3800], [-33.5, -6.0, 3700], [-33.5, -15.0, 3700],
    [-38.0, -22.0, 3800], [-42.0, -28.0, 3900], [-47.0, -34.0, 3900], [-51.0, -40.0, 3900],
    [-53.0, -46.0, 3800], [-52.0, -52.0, 3600]]),
 ("nadw_isow", "Iceland-Scotland overflow -> Charlie-Gibbs", "nadw", [
    [-4.0, 63.5, 400], [-8.2, 61.4, 840], [-13.0, 60.0, 1800], [-19.0, 59.0, 2500],
    [-25.0, 57.0, 2900], [-30.0, 55.0, 3200], [-34.5, 52.5, 3500], [-40.0, 52.5, 3400],
    [-45.0, 52.0, 3300], [-49.0, 50.0, 3200], [-50.0, 46.0, 3100], [-48.0, 43.0, 3000]]),
]

# Antarctic Bottom Water, the abyssal limb. Four sources, three basins.
AABW = [
 ("aabw_weddell", "Weddell Sea bottom water -> Atlantic", "aabw", [
    [-40.0, -73.5, 500], [-44.0, -70.0, 2000], [-42.0, -66.0, 3500], [-38.0, -63.0, 4200],
    [-32.0, -61.0, 4500], [-27.0, -58.5, 4600], [-30.0, -54.0, 4700], [-36.0, -49.0, 4800],
    [-43.0, -44.0, 4900], [-45.0, -38.0, 4800], [-39.3, -31.2, 4650], [-35.0, -25.0, 4700],
    [-31.0, -18.0, 4800], [-29.0, -11.0, 4800], [-25.0, -5.0, 4600], [-18.0, 0.0, 4350],
    [-12.0, 2.0, 4600], [-6.0, 1.0, 4800], [0.0, -3.0, 5000], [4.0, -10.0, 5100]]),
 ("aabw_ross", "Ross Sea bottom water -> Pacific", "aabw", [
    [178.0, -77.5, 500], [176.0, -74.0, 1800], [172.0, -70.0, 3200], [170.0, -66.0, 4200],
    [175.0, -62.0, 4700], [-178.0, -58.0, 5000], [-172.0, -52.0, 5100], [-170.0, -44.0, 5000],
    [-172.0, -34.0, 4900], [-174.0, -24.0, 5000], [-177.0, -14.0, 5100], [-179.0, -4.0, 5000],
    [178.0, 6.0, 5200], [175.0, 16.0, 5400], [171.0, 26.0, 5500], [167.0, 36.0, 5400]]),
 ("aabw_adelie", "Adelie / George V bottom water -> Indian", "aabw", [
    [143.0, -65.6, 500], [143.0, -63.8, 2000], [142.0, -61.0, 3500], [138.0, -58.0, 4300],
    [130.0, -56.0, 4600], [120.0, -55.0, 4700], [110.0, -54.0, 4800], [100.0, -52.0, 4900],
    [92.0, -46.0, 4900], [88.0, -38.0, 4800], [86.0, -28.0, 4700], [84.0, -18.0, 4600],
    [82.0, -8.0, 4400], [80.0, -2.0, 4200], [78.0, 5.0, 4000]]),
 ("aabw_darnley", "Cape Darnley / Prydz Bay bottom water", "aabw", [
    [69.0, -66.8, 500], [67.5, -65.4, 2200], [65.5, -63.0, 3600], [66.0, -60.0, 4300],
    [72.0, -57.0, 4600], [80.0, -55.0, 4700], [90.0, -53.0, 4800], [98.0, -51.0, 4900]]),
]

# Where deep water comes back up. The Southern Ocean limb is the dominant one:
# wind-driven upwelling along the ACC brings deep water to the surface at the
# only latitude band with no continental barrier.
UPWELL = [
 ("up_so_pac",  "Southern Ocean upwelling", "up", [[-150.0, -62.0, 2600], [-150.0, -58.0, 1200], [-150.0, -54.0, 200]]),
 ("up_so_atl",  "Southern Ocean upwelling", "up", [[-25.0, -62.0, 2600], [-25.0, -58.0, 1200], [-25.0, -54.0, 200]]),
 ("up_so_ind",  "Southern Ocean upwelling", "up", [[80.0, -62.0, 2600], [80.0, -58.0, 1200], [80.0, -54.0, 200]]),
 ("up_so_ind2", "Southern Ocean upwelling", "up", [[150.0, -62.0, 2600], [150.0, -58.0, 1200], [150.0, -54.0, 200]]),
 ("up_npac",    "North Pacific diffuse upwelling", "up", [[166.0, 36.0, 5400], [172.0, 42.0, 3000], [178.0, 48.0, 900], [-178.0, 52.0, 150]]),
 ("up_nind",    "North Indian diffuse upwelling", "up", [[78.0, 5.0, 4000], [72.0, 9.0, 2400], [66.0, 14.0, 800], [61.0, 18.0, 150]]),
]

# Sinking. Short, near-vertical, at the formation sites; these are the pump.
SINK = [
 ("sink_nordic",   "Nordic Seas convection",   "sink", [[-5.0, 73.0, 50], [-6.0, 71.5, 900], [-7.0, 70.0, 2000], [-8.0, 68.5, 2800]]),
 ("sink_labrador", "Labrador Sea convection",  "sink", [[-55.0, 57.5, 50], [-55.0, 56.5, 800], [-55.0, 55.5, 1600], [-55.0, 54.5, 2200]]),
 ("sink_weddell",  "Weddell Sea dense shelf",  "sink", [[-40.0, -74.5, 50], [-40.0, -74.0, 600], [-40.0, -73.5, 1400], [-41.0, -72.5, 2400]]),
 ("sink_ross",     "Ross Sea dense shelf",     "sink", [[178.0, -78.0, 50], [178.0, -77.6, 600], [178.0, -77.2, 1400], [177.0, -76.4, 2400]]),
 ("sink_adelie",   "Adelie / George V dense shelf", "sink", [[143.5, -66.3, 50], [143.4, -66.1, 600], [143.3, -65.9, 1400], [143.2, -65.5, 2400]]),
 ("sink_darnley",  "Cape Darnley dense shelf", "sink", [[69.3, -67.2, 50], [69.2, -67.1, 600], [69.1, -67.0, 1400], [68.9, -66.7, 2400]]),
]

LIMBS = WARM + NADW + AABW + UPWELL + SINK
