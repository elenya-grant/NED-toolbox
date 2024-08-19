from toolbox.tools.wind_layout_tools import make_site_boundaries_for_square_layout
import numpy as np
from toolbox.simulation.ned_site import Site, NedManager
import copy
def update_hopp_config_for_wind_capacity(wind_capacity_mw,ned_man:NedManager,hopp_config):
    hopp_config_wind = copy.deepcopy(hopp_config)
    if wind_capacity_mw>0:
        n_turbs = int(wind_capacity_mw/ned_man.turbine_size_mw)
        hopp_config_wind["site"]["wind"] = True
        site_dict = make_site_boundaries_for_square_layout(n_turbs,ned_man.rotor_diameter,ned_man.row_spacing_D,ned_man.turbine_spacing_D)

        hopp_config_wind["technologies"].update({"wind":ned_man.wind_technologies_config_default})
        hopp_config_wind["technologies"]["wind"]["num_turbines"] = n_turbs
    else:
        if "wind" in hopp_config["technologies"]:
            hopp_config_wind["technologies"].pop("wind")
        x = ned_man.site_resolution_km*1e3
        verts = [[0.0,0.0],[0.0,x],[x,x],[x,0.0]]
        site_dict =  {"site_boundaries":{"verts":verts,"verts_simple":verts}}
        hopp_config_wind["site"]["wind"] = False
    hopp_config_wind["site"]["data"].update(site_dict)
    return hopp_config_wind

def update_hopp_config_for_solar_capacity(pv_capacity_mwac,ned_man:NedManager,hopp_config):
    hopp_config_pv = copy.deepcopy(hopp_config)
    if pv_capacity_mwac>0:
        hopp_config_pv["site"]["solar"] = True
        pv_capacity_kwdc = pv_capacity_mwac*ned_man.dc_ac_ratio*1e3
        hopp_config_pv["technologies"].update({"pv":ned_man.pv_technologies_config_default})
        hopp_config_pv["technologies"]["pv"]["system_capacity_kw"] = pv_capacity_kwdc
    else:
        hopp_config_pv["site"]["solar"] = False
        if "pv" in hopp_config_pv["technologies"]:
            hopp_config_pv["technologies"].pop("pv")
    return hopp_config_pv


def update_hopp_config_for_battery(include_battery,ned_man:NedManager,hopp_config):
    hopp_config_bat = copy.deepcopy(hopp_config)
    if include_battery:
        hopp_config_bat["technologies"].update({"battery":ned_man.battery_technologies_config_default})
    else:
        if "battery" in hopp_config_bat["technologies"]:
            hopp_config_bat["technologies"].pop("battery")
    return hopp_config_bat