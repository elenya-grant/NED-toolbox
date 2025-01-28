import pandas as pd
import os
from toolbox.utilities.file_tools import load_dill_pickle
import toolbox.finance_reruns.profast_reverse_tools as rev_pf_tools
import copy
from greenheart.tools.profast_tools import create_and_populate_profast, run_profast
import numpy as np
def calc_life_avg_h2_prod_from_profast(lcoh_pf_config):
    rated_h2_capac_kg_pr_day = lcoh_pf_config["params"]["capacity"]
    annual_rated_h2 = rated_h2_capac_kg_pr_day*365
    annual_h2_pr_yr = [annual_rated_h2*v for k,v in lcoh_pf_config['params']['long term utilization'].items()]

    return annual_h2_pr_yr

def find_min_lcoh_design(lcoh_simplex_data,lcoh_type,atb_scenario = "Moderate"):
    # find lowest lcoh without battery
    lcoh_simplex = copy.deepcopy(lcoh_simplex_data)
    lcoh_simplex = lcoh_simplex[lcoh_simplex["atb_scenario"]==atb_scenario]
    lcoh_simplex = lcoh_simplex[lcoh_simplex["re_plant_type"]=="wind-pv"]
    lcoh_simplex = lcoh_simplex.reset_index(drop=True)
    i_min = lcoh_simplex[lcoh_type].idxmin()
    opt_lcoh = lcoh_simplex.loc[i_min].to_dict()
    lcoh_pf_config = rev_pf_tools.convert_pf_res_to_pf_config(lcoh_simplex.loc[i_min][f"{lcoh_type}_pf_config"])
    opt_lcoh.update({f"{lcoh_type}_pf_config":lcoh_pf_config})
    h2_prod_pr_year = calc_life_avg_h2_prod_from_profast(lcoh_pf_config)
    opt_lcoh.update({"H2 production per year [kg/year]":h2_prod_pr_year})
    opt_lcoh.update({"Life: Annual H2 production [kg/year]":np.mean(h2_prod_pr_year)})
    opt_lcoh_df = pd.Series(opt_lcoh,name=lcoh_type)
    lcoh_cols = [k for k in opt_lcoh_df.index.to_list() if "lcoh" in k]
    drop_cols = [k for k in lcoh_cols if lcoh_type not in k]
    rename_cols = [k for k in lcoh_cols if lcoh_type in k]
    new_cols = [k.replace(lcoh_type,"lcoh") for k in rename_cols]
    colname_map = dict(zip(rename_cols,new_cols))
    opt_lcoh_df = opt_lcoh_df.drop(index=drop_cols)
    
    return opt_lcoh_df.rename(index=colname_map)

def run_min_lcoh_for_site(res_dir,site_id,state=None,lat=None,lon=None):
    if state==None:
        files = os.listdir(res_dir)
        files = [f for f in files if "LCOH_Simplex" in f]
        site_files = [f for f in files if f.split("-")[0]==str(site_id)]
        site_fpath = os.path.join(res_dir,site_files[0])
        site_desc = site_files[0].split("--LCOH_Simplex")[0]
        state = site_desc.split("-")[-1]
        lat_lon = site_desc.replace(f"{site_id}-","").replace(f"-{state}","")
        lat,lon = lat_lon.split("_")
        lat = float(lat)
        lon = float(lon)
    else:
        filename = f"{id}-{lat}_{lon}-{state}--LCOH_Simplex.pkl"
        site_fpath = os.path.join(res_dir,filename)

    data = load_dill_pickle(site_fpath)
    
    lcoh_prod_res = find_min_lcoh_design(data,'lcoh-produced',atb_scenario = "Moderate")
    lcoh_del_res = find_min_lcoh_design(data,'lcoh-delivered',atb_scenario = "Moderate")
    site_res = pd.concat([lcoh_prod_res,lcoh_del_res],axis=1).T
    site_res.index.name = "lcoh type"
    # site_res.reset_index(drop=True)
    site_res["state"] = state
    site_res["id"] = site_id
    
    site_res["latitude"] = lat
    site_res["longitude"] = lon
    site_res = site_res.set_index(keys = ["id"],append=True).swaplevel()
    return site_res

