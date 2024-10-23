import os
import pandas as pd
import numpy as np
from toolbox.utilities.ned_logger import site_logger as slog

def load_simplex_timeseries_for_site(ned_site,storage_desc,prev_run_main_output_dir,prev_run_sweep_name,prev_run_subsweep_names,prev_run_atb_year):
    results_dir = os.path.join(prev_run_main_output_dir,prev_run_sweep_name)
    wind_generation_profiles = {}
    
    folders = [os.path.join(results_dir,sub_dir,"ATB_{}".format(prev_run_atb_year)) for sub_dir in prev_run_subsweep_names]
    for folder in folders:
        files = os.listdir(folder)
        site_files = [f for f in files if f.split("-")[0] == str(ned_site.id)]
        generation_files = [f for f in site_files if "WindGenerationProfiles.pkl" in f]
        ts_filepath = os.path.join(folder,generation_files[0])
        if os.path.isfile(ts_filepath):
            df_ts = pd.read_pickle(ts_filepath).to_dict()
            wind_generation_profiles.update(df_ts)
        else:
            slog.warning("Site {}: optimized generation file does not exist \n {}".format(ned_site.id,ts_filepath))

    return wind_generation_profiles

def load_baseline_timeseries_for_site(ned_site,storage_desc,prev_run_main_output_dir,prev_run_sweep_name,prev_run_subsweep_names,prev_run_atb_year):
    #storage_desc = "onsite_storage"
    #prev_run_sweep_name = "offgrid-baseline"
    #prev_run_subsweep_names = ["over-sized","equal-sized","under-sized"]
    #prev_run_atb_year = 2030
    #prev_run_main_output_dir = "/projects/hopp/ned-results/v1"
    n_decimals = 1
    results_dir = os.path.join(prev_run_main_output_dir,prev_run_sweep_name)
    wind_generation_profiles = {}
    pv_generation_profiles = {}
    folders = [os.path.join(results_dir,sub_dir,"ATB_{}".format(prev_run_atb_year)) for sub_dir in prev_run_subsweep_names]
    for folder in folders:
        files = os.listdir(folder)
        site_files = [f for f in files if f.split("-")[0] == str(ned_site.id)]
        site_files = [f for f in site_files if storage_desc in f]
        sum_files = [f for f in site_files if "--Summary" in f]
        ts_files = [f for f in site_files if "--Physics_Timeseries" in f]
        ts_filepath = os.path.join(folder,ts_files[0])
        sum_filepath = os.path.join(folder,sum_files[0])

        if os.path.isfile(ts_filepath) and os.path.isfile(sum_filepath):
            df_ts = pd.read_pickle(ts_filepath)
            df_sum = pd.read_pickle(sum_filepath).to_dict()["Physics"]
            for re_plant_type in df_ts["re_plant_type"].to_list():

                re_sum = df_sum[df_sum["re_plant_type"]==re_plant_type]
                re_sum = re_sum["renewables_summary"].iloc[0]
                ts = df_ts[df_ts["re_plant_type"]==re_plant_type]
                ts = ts["timeseries"].iloc[0]
                if "wind" in re_plant_type:
                    wind_size_mw = round(re_sum["Wind: System Capacity [kW]"]/1e3,n_decimals)
                    wind_timeseries = np.array(ts["Wind Generation"])
                    wind_generation_profiles.update({wind_size_mw:wind_timeseries})
                if "pv" in re_plant_type:
                    pv_size_mwdc = round(re_sum["PV: System Capacity [kW-DC]"]/1e3,n_decimals)
                    pv_timeseries = np.array(ts["PV Generation"])
                    pv_generation_profiles.update({pv_size_mwdc:pv_timeseries})
        else:
            slog.warning("Site {}: baseline files do not exist \n {} \n {}".format(ned_site.id,ts_filepath,sum_filepath))
    return wind_generation_profiles,pv_generation_profiles

