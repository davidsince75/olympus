# -*- coding: utf-8 -*-
"""The Atlas explainer content and machinery."""
import io, sys
SRC = "/home/claude/olympus/src/atlas.html"
s = io.open(SRC, encoding="utf8").read()
def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1: sys.exit("FAIL %s: %d matches" % (label, n))
    s = s.replace(old, new, 1); print("  ok  %s" % label)

BLOCK = u'''
/* ============================ the learning layer ============================
   Same model as the deck: four kinds, one popup, and a provenance line on every
   entry — the rule the whole platform is built on. Two differences here. Hover
   targets sit on the chrome and never on the map, because the map's hover and
   click already belong to the stations. And a small set of anchored callouts is
   drawn on the map when LEARN is on, to say what the network shows rather than
   what a word means.                                                          */

const EXKIND = {obj:"OBJECT", ins:"INSTRUMENT", num:"NUMBER", mech:"FINDING"};
const EXPL = {

/* ---- what the register is ---- */
counts:{k:"num",t:"166 facilities",
 b:"<b>114 in the Antarctic, 52 in the Arctic.</b> Not every building on the ice — every facility that has a position, an operator and a reason to be counted: year-round bases, summer camps, observatories, runways, depots, drifting platforms and the support bases that feed them. Gateway ports and heritage huts are counted separately and drawn differently, because they are not facilities.",
 p:"Antarctic from the COMNAP master list plus researched additions; Arctic compiled. See the provenance line in the footer."},
operators:{k:"num",t:"40 operators",
 b:"Operators, not countries. Most are national programmes, but not all: <b>ALCI</b> and <b>Antarctic Logistics &amp; Expeditions</b> are commercial, the <b>International Polar Foundation</b> is a charity, and several facilities are run by two programmes together. The count went from 41 to 40 when a research project that had been filed as an operator was removed.",
 p:"Distinct operator values across the register. The correction is described under Project, not operator."},
openness:{k:"num",t:"The axis nobody else publishes",
 b:"Every facility is scored on one question: <b>can a curious person outside the institution see any of it?</b> Not whether it does good science — that is a different question and other people already answer it. <b>48 open · 35 partial · 67 minimal · 16 opaque.</b> The largest group is minimal, which is the finding: most of what happens on the ice is invisible from outside.",
 p:"Scored per facility against the scale in the register's meta.openness_scale."},
open_level:{k:"obj",t:"Open",
 b:"A public presence at the level of the station itself, <b>and</b> either a live feed or machine-readable data you can actually fetch. Forty-eight facilities. Zackenberg, which publishes thirty years of one valley's ecology, is the type specimen.",
 p:"Both conditions must hold. A handsome page with nothing behind it is Partial."},
partial_level:{k:"obj",t:"Partial",
 b:"There is a public presence, and the data exists, but it reaches you through a national portal or on request rather than from the station. Thirty-five facilities. This is the most common shape of a well-run programme that has not thought about the public as an audience.",
 p:"Scored where data is reachable but not directly, or where the station page is the operator's."},
minimal_level:{k:"obj",t:"Minimal",
 b:"An operator-level presence only — you can establish that the place exists and who runs it, and little else specific to it. <b>Sixty-seven facilities, the largest single group.</b> Not secrecy, mostly: just nobody whose job it is.",
 p:"The modal state of the register, which is itself the point."},
opaque_level:{k:"obj",t:"Opaque",
 b:"No meaningful public presence in a language a general reader can reach. Sixteen facilities. This is a statement about <b>reachability, not about worth</b> — several of these are serious scientific stations. But if you wanted to know what one of them measured this year, you could not find out.",
 p:"Scored on public reachability alone. No judgement of the science is implied or intended."},
gateway:{k:"obj",t:"Gateway ports",
 b:"Eleven cities, drawn as open rings because they are not on the ice. Almost everything and everyone that reaches Antarctica passes through one of them — Hobart, Christchurch, Punta Arenas, Ushuaia, Cape Town. They are the real chokepoints of the continent, and they are all in the temperate world.",
 p:"Compiled from national programme logistics publications."},
heritage:{k:"obj",t:"Heritage sites",
 b:"Thirteen, drawn as diamonds. Huts and sites protected under the Antarctic Treaty system, several of them still standing within sight of a working station — <b>Scott's Discovery hut is 300 m from McMurdo's dormitories</b>, with the seal blubber still in the stove. The continent's history and its present are usually the same view.",
 p:"Antarctic Treaty Historic Sites and Monuments, selected."},
facility_vs_programme:{k:"obj",t:"Project, not operator",
 b:"A record here describes <b>a place and who runs it</b>. A research project that works at that place goes in <i>Programmes hosted</i>, never in the operator or the nation. The rule exists because it was broken: Beyond EPICA — an EU-funded project, one of about twenty in the EU Polar Cluster — had been filed as the operator and the nation of Little Dome C, which is in fact a French and Italian camp 35 km from Concordia.",
 p:"Carried in the data as meta.schema_note, so it survives a rebuild by anyone."},
joint:{k:"obj",t:"Shared facilities",
 b:"Some stations are run by two programmes at once, and the register records both. <b>AWIPEV</b> is a German and a French station merged into one building; <b>Concordia</b> and the <b>Little Dome C</b> drill camp are both French and Italian. In the Arctic this is rarer than it sounds, and in the Antarctic it is one of the few things the Treaty system reliably produces.",
 p:"The joint field on each record; drawn as a joint edge on the network."},

/* ---- where it comes from ---- */
comnap:{k:"ins",t:"The master list, and its date",
 b:"The Antarctic half rests on the <b>COMNAP Antarctic Facilities Master List, 2017 edition</b>, and every record says so. That is the weakest thing in this dataset and it is stamped rather than hidden: eight years of openings, closures and rebuilds have happened since. Post-2017 facilities were researched one at a time — Qinling, Union Glacier, Novo Runway, Troll Airfield, Perseus and Little Dome C.",
 p:"COMNAP master list, 2017 edition, redistributed with Quantarctica 3. Asking COMNAP for a current edition is an open action."},
arctic_register:{k:"ins",t:"The Arctic list had to be built",
 b:"There is <b>no COMNAP for the north</b>. No single body keeps a register of Arctic research facilities, because there is no single treaty and eight sovereign states own the ground. So these 52 were selected — for bearing on the cryosphere — from operator and programme publications: the Ny-Ålesund cluster, the Greenland ice-sheet camps, the Canadian High Arctic observatories, the Siberian shelf stations, the Fennoscandian observatories and the drifting platform.",
 p:"Compiled. Positions to station-site precision from operator and programme publications, 2026."},
link_rot:{k:"ins",t:"Every link was tried",
 b:"Before publication each outbound URL was fetched and the result recorded: <b>96 verified live, 4 blocked to robots, 5 unverifiable from the build host</b>. Dead links are shown as dead rather than left looking healthy. Eight of the first 118 were already wrong when first checked, which is roughly a 7% annual rot rate — so this check has to be scheduled, not done once.",
 p:"Recorded in the data as meta.links_checked and per record as link_status."},
positions:{k:"ins",t:"How exact a position is",
 b:"Antarctic coordinates come from the master list and are good to the site. Arctic coordinates are compiled from operator publications and are good to the <b>station site, not to the building</b> — at Ny-Ålesund nine facilities share three decimal places of longitude because they share a village. Each record carries its own provenance for geometry, population and narrative separately, because they have different reliability.",
 p:"The prov block on every record: geo, demog and narrative, sourced independently."},
edges:{k:"ins",t:"Six kinds of line",
 b:"Kept separate because they mean different things. <b>Air</b> (54) and <b>sea</b> (22) are how people and cargo arrive. <b>Traverse</b> (13) is overland by tractor train. <b>Cluster</b> (37) means near enough to walk or ski between. <b>Joint</b> (4) means one facility run by two programmes. <b>Record</b> (12) links places that share a scientific series rather than any physical route.",
 p:"142 edges. Compiled from operator logistics publications and programme documentation."},
routes:{k:"ins",t:"The lines are not tracks",
 b:"Every route is drawn as a <b>schematic great circle</b> between two published positions. No flight actually follows it: aircraft route around weather, fuel and the blue-ice runway that happens to be usable that week, and ships follow the ice edge. The line asserts a connection, never a path.",
 p:"Drawn geometry, stated in the footer of every view."},
search:{k:"ins",t:"What the search sees",
 b:"Name, official name, operator, nation, region, locality, what the facility observes, and the programmes it hosts — all of it, in one haystack. So <b>ozone</b> finds the stations that measure it and <b>Ny-Ålesund</b> finds all nine at once, and neither is a special case anybody coded.",
 p:"One flattened string per record, rebuilt when the register is."},
projection:{k:"ins",t:"The projection, stated honestly",
 b:"A <b>spherical polar stereographic disc normalised at 45°</b>. It is not EPSG:3031 or EPSG:3413, and it does not claim to be. That is why the satellite imagery here is resampled through this surface's own inverse projection rather than drawn as published tiles — alignment by construction instead of by coincidence. Drawing the real tiles is a projection change and it has not been made.",
 p:"proj() in this page. The coastlines and every station position pass through the same function."},

/* ---- the living layer, shared with the deck ---- */
ovation:{k:"ins",t:"The aurora is a forecast",
 b:"Not a photograph, and stamped <b>MODEL</b> for that reason. A spacecraft at L1, 1.5 million km upstream, measures the solar wind speed and the interplanetary magnetic field; OVATION-Prime turns those into the energy flux of particles precipitating into the atmosphere, from which a viewing probability follows. The roughly half-hour lead time is nothing more than how long the solar wind takes to cross the remaining distance to Earth.",
 p:"NOAA SWPC OVATION-Prime 30-minute forecast, both hemispheres."},
kp_index:{k:"num",t:"Kp",
 b:"The largest wobble in the horizontal magnetic field over three hours, scaled 0 to 9, averaged across <b>thirteen ground observatories</b> — all of them between 44° and 60° geomagnetic latitude, none of them anywhere near the poles. Five or above is a geomagnetic storm. Read it as a planetary weather report, not as what any one station on this map is seeing tonight.",
 p:"NOAA SWPC estimated planetary K index; definitive Kp from GFZ Potsdam."},
drift_cmcc:{k:"ins",t:"How you measure ice moving",
 b:"You photograph the pack twice, 48 hours apart, and find the displacement that best matches each patch of the first image to the second — maximum cross-correlation. The <b>continuous</b> version used here refines that match between pixels instead of snapping to the grid, which removes most of the quantisation noise. Inputs are SSMIS at 91 GHz, ASCAT and AMSR2.",
 p:"EUMETSAT OSI SAF OSI-405-c, 62.5 km grid. Only nominal-quality vectors — status flag 30 — are drawn."},
drift_true_length:{k:"num",t:"Why the arrows look short",
 b:"At ×1 they are drawn at <b>true length</b>. Pack ice typically travels a few kilometres a day, so two days of motion is often less than a single 62.5 km cell — the vector is genuinely shorter than the grid it sits on. Any exaggeration is a lie unless it is labelled, which is why the multiplier is named on screen whenever it is not 1.",
 p:"48-hour displacement. At ×1 the head and tail are both real positions."},
sar_s1:{k:"ins",t:"Radar that makes its own light",
 b:"Sentinel-1 carries a C-band synthetic aperture radar at <b>5.405 GHz</b>. It is active — it illuminates the surface itself, so cloud and polar night are irrelevant to it. Over sea ice it runs in Extra Wide mode, five sub-swaths stitched into a 410 km strip at 20 × 40 m. Sentinel-1A was retired in July 2026; the 6-day repeat is now flown by 1C and 1D.",
 p:"ESA Copernicus Sentinel-1 mission specification."},
sar_footprints:{k:"obj",t:"Footprints, not pictures",
 b:"Each outline is <b>where the radar was pointed</b> in the last 18 hours, from the Copernicus catalogue of acquisitions — the metadata, not the imagery. The scene behind one of these polygons is a separate download of several hundred megabytes. Look at where they cluster: that is where somebody decided the ice was worth watching this week.",
 p:"Copernicus Data Space Ecosystem OData catalogue, both polar caps, 18-hour window."},
truecolor:{k:"ins",t:"True colour, and what it is not",
 b:"One day of real reflectance from MODIS: red is band 1, green band 4, blue band 3, at <b>250 m</b>. Called <i>corrected</i> reflectance because Rayleigh scattering and gas absorption have been removed — but aerosols deliberately have not, so smoke and haze stay visible instead of being scrubbed out. Where it goes black, that is polar night, not missing data.",
 p:"NASA GIBS / Worldview MODIS Corrected Reflectance, produced by LANCE."},
bluemarble:{k:"obj",t:"Blue Marble",
 b:"A static composite — shaded relief and <b>bathymetry</b>, so the sea floor is drawn as well as the land. Worth turning on when looking at the Southern Ocean: the pale ring around the continent is the continental shelf, and the step where it ends is where the dense water made in the coastal polynyas descends into the deep ocean.",
 p:"NASA GIBS BlueMarble_ShadedRelief_Bathymetry. A composite with no date."},
live_transport:{k:"ins",t:"What live means here",
 b:"A published artifact cannot fetch anything at runtime — no network of any kind reaches it. So these layers are <b>baked at build time and stamped with their own observation time</b>, never with the build time. The same page built for a web host sets a flag and refreshes the fast layers from the identical endpoints in the browser. One data model, two transports.",
 p:"ingest/build_events.py writes both. This copy carries the snapshot."},
age_stamp:{k:"num",t:"Every layer states its own age",
 b:"These ages count from the <b>observation</b>, not from the build. A two-hour-old radar footprint and a day-old drift field are both correct and they mean different things, so there is no single last-updated time on this map and there should not be one. Collapsing them into one number would be the most convenient available lie.",
 p:"Each source carries its own observation timestamp through ingest to the page."},
scale:{k:"num",t:"Scale, and what it costs",
 b:"The bar is honest at the centre of the disc and increasingly wrong towards its edge — that is what a stereographic projection does, and it is why the scale is recomputed as you zoom. Distances between two stations on opposite sides of the disc should be read from their coordinates, not from this bar.",
 p:"Computed from the current zoom against the disc radius."},
both_poles:{k:"obj",t:"Both poles at once",
 b:"Two discs, same scale, and the asymmetry is the first thing to see. The Antarctic is a continent surrounded by ocean and governed by a treaty with no owner; the Arctic is an ocean surrounded by <b>eight sovereign states</b>, and every station in the north stands on somebody's territory. Almost everything else about how the two registers behave follows from that one difference.",
 p:"Same projection applied to both hemispheres; nothing is mirrored or reused."},
surfaces:{k:"obj",t:"Three surfaces",
 b:"This is one of three. The <b>Deck</b> is the instrument: measured sea ice back to 1978, the overturning circulation, and the living layers. <b>Stations</b> is this — who is actually on the ice. <b>Named Ice</b> is the cultural surface, where the ice has words rather than values. Same data model, same palette, three registers.",
 p:"All three are separate builds. The payload ceiling applies to each surface rather than to the platform."},

/* ---- what the network shows: the map callouts ---- */
finding_dml:{k:"mech",t:"Two runways for a third of a continent",
 b:"Nineteen facilities sit in Dronning Maud Land, run by nine national programmes and two logistics operators, and almost all of them are reached through <b>two blue-ice runways</b> — Novo, run by a commercial consortium beside a Russian station, and Troll, run by Norway. Perseus has since been added as a third. A single bad season at Novo would strand a large part of the continent's science, and there is no redundancy anywhere in that sentence.",
 p:"Counted from this register: facilities between 20°W and 45°E, south of 68°S."},
finding_fildes:{k:"mech",t:"Six stations you could walk between",
 b:"On the Fildes Peninsula, within <b>2 km</b> of each other, sit four Chilean facilities, Russia's Bellingshausen and China's Great Wall — with Uruguay's Artigas 3.6 km further and Korea's King Sejong 9.5 km along the coast. It is the densest patch of Antarctic infrastructure anywhere, it has a gravel runway, and it is the reason King George Island is where most people who go to Antarctica actually land.",
 p:"Great-circle distances computed from the positions in this register."},
finding_union:{k:"mech",t:"A private runway several countries now need",
 b:"Union Glacier Camp is run by a <b>commercial expedition company</b>, and it is the only place in Antarctica where a private operator and national programmes share a runway. Several national programmes now route people and cargo through it. Whether that is efficiency or a dependency is a question the Treaty system has not really answered.",
 p:"Antarctic Logistics &amp; Expeditions; researched addition, post-2017."},
finding_russia:{k:"mech",t:"The largest programme, and the least legible",
 b:"Russia operates <b>19 facilities across both poles — 12 south, 7 north, 14 of them year-round</b>, more than any other operator in this register. Not one of them scores <i>open</i>: thirteen are opaque, four minimal, two partial. That is the single sharpest illustration of why this map scores reachability separately from size, because on size alone Russia is the most present nation on the ice.",
 p:"Counted from this register. The score is about public reachability, not about the science."},
finding_nyalesund:{k:"mech",t:"Ten nations in one village",
 b:"Ny-Ålesund, 78.9°N, is a former coal-mining settlement with <b>nine research facilities belonging to ten countries</b> — China, France, Germany, India, Italy, Japan, the Netherlands, Norway, South Korea and the United Kingdom — sharing a few hundred metres of shoreline. It is the closest thing the Arctic has to the Antarctic Treaty system, and it exists because Norway allows it under the 1920 Svalbard Treaty rather than because anyone agreed to it.",
 p:"Counted from this register. AWIPEV is a single facility run jointly by Germany and France."},
finding_terranova:{k:"mech",t:"Four countries at Terra Nova Bay",
 b:"Italy, Korea, Germany and China all hold facilities within <b>40 km</b> of each other on the Ross Sea coast. The newest is <b>Qinling</b>, which China opened on 7 February 2024 on Inexpressible Island — the island where Scott's Northern Party wintered in a snow cave in 1912 and very nearly did not come out.",
 p:"Great-circle distances computed from the positions in this register."}
};
'''

# put the block just before the state object so everything after can use it
once(u'const st = {\n  mode:"S", sel:null, hover:null, q:"",', BLOCK + u'\nconst st = {\n  mode:"S", sel:null, hover:null, q:"",', "EXPL block")
io.open(SRC, "w", encoding="utf8").write(s)
print("expl written")
