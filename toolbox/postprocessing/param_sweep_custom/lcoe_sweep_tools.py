import pandas as pd
import os
from toolbox.utilities.file_tools import dump_data_to_pickle,check_create_folder,load_dill_pickle
import toolbox.finance_reruns.profast_reverse_tools as rev_pf_tools
import copy
from greenheart.tools.profast_tools import create_and_populate_profast, run_profast

def calc_aep_from_profast(lcoe_opt_res):
    daily_energy_production_kWh = lcoe_opt_res["params"]["capacity"]
    annual_energy_production_kWh = daily_energy_production_kWh*365
    return annual_energy_production_kWh

def find_min_lcoe_design(lcoe_simplex_data,atb_scenario = "Moderate"):
    # find lowest lcoe without battery
    lcoe_simplex = copy.deepcopy(lcoe_simplex_data)
    lcoe_simplex = lcoe_simplex[lcoe_simplex["atb_scenario"]==atb_scenario]
    lcoe_simplex = lcoe_simplex[lcoe_simplex["re_plant_type"]=="wind-pv"]
    lcoe_simplex = lcoe_simplex.reset_index(drop=True)
    i_min = lcoe_simplex["lcoe"].idxmin()
    opt_lcoe = lcoe_simplex.loc[i_min].to_dict()
    lcoe_pf_config = rev_pf_tools.convert_pf_res_to_pf_config(lcoe_simplex.loc[i_min]["lcoe_pf_config"])
    opt_lcoe.update({"lcoe_pf_config":lcoe_pf_config})
    hybrid_aep_kWh = calc_aep_from_profast(lcoe_pf_config) #this is unconstrained AEP
    opt_lcoe.update({"annual_energy_produced_by_renewables_kWh":hybrid_aep_kWh})


    # get battery profast dict for the above plant design
    lcoe_simplex_bat = lcoe_simplex_data[lcoe_simplex_data["atb_scenario"]==atb_scenario]
    lcoe_simplex_bat = lcoe_simplex_bat[lcoe_simplex_bat["re_plant_type"]=="wind-pv-battery"]
    lcoe_simplex_bat = lcoe_simplex_bat[lcoe_simplex_bat["wind_size_mw"]==opt_lcoe["wind_size_mw"]]
    lcoe_simplex_bat = lcoe_simplex_bat[lcoe_simplex_bat["pv_size_mwdc"]==opt_lcoe["pv_size_mwdc"]]
    opt_lcoe_bat = lcoe_simplex_bat.iloc[0].to_dict()
    lcoe_pf_config_bat = rev_pf_tools.convert_pf_res_to_pf_config(lcoe_simplex_bat.iloc[0]["lcoe_pf_config"])
    hybrid_aep_kWh_to_elec = calc_aep_from_profast(lcoe_pf_config_bat) #this is constrained by energy to electrolyzer when using battery
    opt_lcoe_bat.update({"annual_energy_to_electrolyzer_with_battery_kWh":hybrid_aep_kWh_to_elec})
    lcoe_pf_config_bat["params"].update({"capacity":hybrid_aep_kWh})
    # lcoe_simplex_bat = lcoe_simplex_bat.reset_index(drop=True)
    #recalc lcoe for total energy produced but including battery capex
    opt_lcoe_bat.update({"lcoe_pf_config":lcoe_pf_config_bat})
    pf_bat = create_and_populate_profast(lcoe_pf_config_bat)
    sol,summary,price_breakdown = run_profast(pf_bat)
    opt_lcoe_bat.update({"lcoe":sol['price']})

    #
    opt_lcoe_bat.update({"annual_energy_produced_by_renewables_kWh":hybrid_aep_kWh})
    opt_lcoe.update({"annual_energy_to_electrolyzer_with_battery_kWh":hybrid_aep_kWh_to_elec})

    opt_res = pd.concat([pd.Series(opt_lcoe,name='wind-pv'),pd.Series(opt_lcoe_bat,name= 'wind-pv-battery')],axis=1)
    return opt_res.T

def run_min_lcoe_for_site(res_dir,site_id,state=None,lat=None,lon=None):
    
    if state==None:
        files = os.listdir(res_dir)
        files = [f for f in files if "LCOE_Simplex" in f]
        site_files = [f for f in files if f.split("-")[0]==str(site_id)]
        site_fpath = os.path.join(res_dir,site_files[0])
        site_desc = site_files[0].split("--LCOE_Simplex")[0]
        state = site_desc.split("-")[-1]
        lat_lon = site_desc.replace(f"{site_id}-","").replace(f"-{state}","")
        lat,lon = lat_lon.split("_")
        lat = float(lat)
        lon = float(lon)
    else:
        filename = f"{id}-{lat}_{lon}-{state}--LCOE_Simplex.pkl"
        site_fpath = os.path.join(res_dir,filename)

    data = load_dill_pickle(site_fpath)
    site_res = find_min_lcoe_design(data,atb_scenario = "Moderate")
    site_res.reset_index(drop=True)
    site_res["state"] = state
    site_res["id"] = site_id
    
    site_res["latitude"] = lat
    site_res["longitude"] = lon
    site_res = site_res.reset_index(drop=True).set_index(keys = "id")
    return site_res
