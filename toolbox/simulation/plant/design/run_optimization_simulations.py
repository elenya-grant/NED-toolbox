import toolbox.simulation.plant.design.optimization_tools as opt_tools
# from toolbox.simulation.run_single_case import run_simple_single_simulation
from hopp.utilities import load_yaml
from toolbox import LIB_DIR, INPUT_DIR
from toolbox.simulation.ned_site import NedManager
import numpy as np
import pandas as pd
import time
import toolbox.simulation.greenheart_management as gh_mgmt
import os
import toolbox.tools.interface_tools as int_tool
from toolbox.simulation.plant.design.simple_optimize_capacities import optimize_design
from toolbox.simulation.plant.design.base_optimization import RenewableGenerationTracker,OptimizationResults, OptimalDesign
from toolbox.simulation.plant.design.site_simplex import SiteSimplex
from toolbox.simulation.sweep_cost_cases_for_optimal_design import sweep_custom_plant_designs
from toolbox.utilities.ned_logger import site_logger as slog
import dill
from toolbox.utilities.file_tools import check_create_folder
from toolbox.tools.load_timeseries_data import load_baseline_timeseries_for_site,load_simplex_timeseries_for_site
from hopp.simulation.technologies.sites import SiteInfo
from toolbox.simulation.results import NedOutputs
from greenheart.simulation.greenheart_simulation import GreenHeartSimulationConfig
from toolbox.simulation.plant.design.base_optimization import OptimizeConfig
from toolbox.simulation.plant.design.run_hopp_for_simplex import loop_wind_solar_battery_designs,update_config_for_lcoh_delivered,update_config_for_lcoh_produced
from toolbox.utilities.ned_logger import site_logger as slog

def run_parametric_sweep(hopp_site:SiteInfo,ned_site:SiteSimplex,ned_man:NedManager,ned_out:NedOutputs,config:GreenHeartSimulationConfig,opt_config:OptimizeConfig):
    # hopp_site,ned_site,ned_man,ned_out,config = opt_tools.initialize_site_for_run(site_info,site_simplex,ned_manager_dict,config_input_dict,ned_output_config_dict,optimization_config)
    # opt_config = opt_tools.make_optimization_config(optimization_config)
    slog.info("Site {}: starting parametric sweep".format(ned_site.id))
    wind_sizes_init,pv_sizes_mwdc_init = ned_site.get_hybrid_sizes_for_making_full_simplex()
    unique_wind_sizes_mw = np.unique(wind_sizes_init)
    unique_pv_sizes_mwdc = np.unique(pv_sizes_mwdc_init)
    unique_pv_sizes_mwac = unique_pv_sizes_mwdc/ned_man.dc_ac_ratio
    start = time.perf_counter()
    if opt_config.use_existing_timeseries_info:
        slog.debug("Site {}: loading timeseries data".format(ned_site.id))
        if "baseline" in opt_config.existing_timeseries_data_info["prev_run_sweep_name"]:
            wind_generation_profiles,pv_generation_profiles = load_baseline_timeseries_for_site(ned_site,**opt_config.existing_timeseries_data_info)
        elif "optimized" in opt_config.existing_timeseries_data_info["prev_run_sweep_name"]:
            wind_generation_profiles = load_simplex_timeseries_for_site(ned_site,**opt_config.existing_timeseries_data_info)
        
        wind_profiles,simplex_results,parametric_sweep_results = loop_wind_solar_battery_designs(unique_wind_sizes_mw,unique_pv_sizes_mwac,ned_site,ned_man,ned_out,config,hopp_site,wind_profiles = wind_generation_profiles)
    else:
        slog.debug("Site {}: running all plant designs".format(ned_site.id))
        wind_profiles,simplex_results,parametric_sweep_results = loop_wind_solar_battery_designs(unique_wind_sizes_mw,unique_pv_sizes_mwac,ned_site,ned_man,ned_out,config,hopp_site)
    # save wind generation profiles
    wind_profile_filename = "{}-{}_{}-{}--WindGenerationProfiles.pkl".format(ned_site.id,ned_site.latitude,ned_site.longitude,ned_site.state.replace(" ",""))
    wind_profile_filepath = os.path.join(ned_man.output_directory,wind_profile_filename)
    pd.Series(wind_profiles).to_pickle(wind_profile_filepath)
    #save parametric sweep results
    parametric_sweep_filepath = ned_site.get_extra_data_simplex_filename(ned_man.output_directory)
    pd.DataFrame(parametric_sweep_results).T.to_pickle(parametric_sweep_filepath)
    #save simplex results
    ned_site.add_full_simplex(simplex_results)
    ned_site.save_full_simplex(output_dir=ned_man.output_directory)
    slog.debug("Site {}: saved parametric sweep results".format(ned_site.id))
    end = time.perf_counter()
    sim_time = round((end-start)/60,3)
    slog.info("Site {}: took {} minutes to run parametric sweep".format(ned_site.id,sim_time))
    return ned_site

def run_site_optimization(site_info,site_simplex,ned_manager_dict,config_input_dict,ned_output_config_dict,optimization_config,run_full_optimization = True):
    start_time = time.perf_counter()

    hopp_site,ned_site,ned_man,ned_out,config = opt_tools.initialize_site_for_run(site_info,site_simplex,ned_manager_dict,config_input_dict,ned_output_config_dict,optimization_config)
    opt_config = opt_tools.make_optimization_config(optimization_config)
    
    simplex_fpath = ned_site.get_full_simplex_filename(output_dir=ned_man.output_directory)
    if os.path.isfile(simplex_fpath):
        simplex_results = pd.read_pickle(simplex_fpath)
        ned_site.add_full_simplex(simplex_results)
        slog.debug("Site {}: loaded simplex from existing results".format(ned_site.id))
    else:
        # start = time.perf_counter()
        slog.debug("Site {}: making simplex".format(ned_site.id))
        ned_site = run_parametric_sweep(hopp_site,ned_site,ned_man,ned_out,config,opt_config)
    if run_full_optimization:
        slog.debug("Site {}: running optimization".format(ned_site.id))
        OptRes = OptimizationResults(site = ned_site)
        opt_tracker = []
        for re_plant_desc in opt_config.optimization_design_list:
            for merit_figure in ned_site.merit_figures:
                start = time.perf_counter()
                if "delivered" in merit_figure:
                    ned_man.baseline_h2_storage_type = opt_config.simplex_design_case["h2_storage_type"]
                    h2_storage_type =  opt_config.simplex_design_case["h2_storage_type"]
                    config = update_config_for_lcoh_delivered(config,ned_man,ned_site)
                else:
                    # ned_man.baseline_h2_storage_type = "none"
                    config = update_config_for_lcoh_produced(config)
                    h2_storage_type = "none"
                if "battery" in re_plant_desc:
                    include_battery = True
                else:
                    include_battery = False
                
                res = optimize_design(ned_site,ned_man,ned_out,config,hopp_site,re_plant_desc,OptRes,merit_figure,h2_storage_type)
                end = time.perf_counter()
                sim_time = round((end-start)/60,3)
                slog.info("Site {}: took {} to optimize {}-{}".format(ned_site.id,sim_time,re_plant_desc,merit_figure))

                ned_site.add_optimization_res(res,re_plant_desc,merit_figure)
                wind_sizes,pv_sizes_mwdc = opt_tools.get_final_runs_to_check_optimal_results(opt_config,res,re_plant_desc)
                
                simplex_optimal_results = opt_tools.run_unique_wind_solar_sizes(wind_sizes,pv_sizes_mwdc,ned_out,ned_man,config,hopp_site,include_battery = include_battery)
                ned_site.optimization_simplex = pd.concat([ned_site.optimization_simplex,simplex_optimal_results])

                idx_optimal = np.argmin(simplex_optimal_results["lcoh"].to_list())
                optimal_wind_size = simplex_optimal_results["wind_size_mw"].loc[idx_optimal]
                optimal_pv_sizedc = simplex_optimal_results["pv_size_mwdc"].loc[idx_optimal]
                optimal_pv_sizeac = optimal_pv_sizedc/ned_man.dc_ac_ratio
                
                slog.info("Site {}: Optimal sizes: {} MW Wind | {} MWdc PV".format(ned_site.id,optimal_wind_size,optimal_pv_sizedc))
                opt_des = OptimalDesign(
                optimization_design_desc=re_plant_desc,
                wind_size_mw=optimal_wind_size,
                pv_capacity_mwac=optimal_pv_sizeac,
                include_battery=include_battery)

                opt_tracker.append(opt_des)
        ned_site.save_optimization_results(ned_man.output_directory)
        ned_site.save_optimization_simplex_results(ned_man.output_directory)
        OptRes.save_Optimization_results(ned_man.output_directory)
        sweep_custom_plant_designs(site_info,
                config_input_dict,
                ned_output_config_dict,
                ned_manager_dict,
                hopp_site,
                custom_plant_designs = opt_tracker)
        
        end_time = time.perf_counter()
        sim_time = round((end_time-start_time)/60,3)
        slog.info("{}: took {} min to completed optimization".format(ned_site.id,sim_time))
    
   
if __name__=="__main__":
    atb_year = 2030
    input_filepath = INPUT_DIR/"v1-optimize-offgrid/main-{}.yaml".format(atb_year)
    optimization_filepath = INPUT_DIR/"v1-optimize-offgrid/optimize_config_{}.yaml".format(atb_year)
    input_config = load_yaml(input_filepath)
    optimization_config = load_yaml(optimization_filepath)
    input_config["hpc_or_local"] = "local"
    input_config["renewable_resource_origin"] = "API"
    if "env_path" in input_config:
        input_config.pop("env_path")
    site_id = 14740 #1
    ned_manager_dict,config_input_dict,ned_output_config_dict,site_list,sitelist_simplex = opt_tools.initialize_optimization_data(input_config,optimization_config)
    site_info = site_list.loc[site_id].to_dict()
    if sitelist_simplex is not None:
        site_simplex = sitelist_simplex.loc[site_id]
    else:
        site_simplex = None
    run_site_optimization(site_info,site_simplex,ned_manager_dict,config_input_dict,ned_output_config_dict,optimization_config,run_full_optimization=False)
