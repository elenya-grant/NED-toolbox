from toolbox.simulation.run_offgrid_onshore import setup_runs, check_config_values, update_config_for_site, update_config_for_baseline_cases
from toolbox import SITELIST_DIR
from toolbox import LIB_DIR, INPUT_DIR
from hopp.utilities import load_yaml
import os
from toolbox.preprocessing.get_simplex_sitelist_from_baseline_cases import make_sitelist_simplex_baseline_offgrid
import pandas as pd
from toolbox.simulation.ned_site import Site, NedManager
from hopp.simulation.technologies.sites import SiteInfo
from toolbox.simulation.results import NedOutputs
from greenheart.simulation.greenheart_simulation import GreenHeartSimulationConfig
from toolbox.simulation.plant.design.site_simplex import SiteSimplex
import numpy as np
import toolbox.tools.interface_tools as int_tool
import toolbox.simulation.greenheart_management as gh_mgmt
from toolbox.simulation.run_single_case import run_simple_single_simulation
import copy
from toolbox.simulation.run_single_case import update_renewable_plant_design
from toolbox.simulation.plant.design.base_optimization import RenewableGenerationTracker,DesignVariable,OptimizeConfig
from toolbox.utilities.ned_logger import site_logger as slog

def get_final_runs_to_check_optimal_results(opt_config,res,re_plant_desc):
    for i,var in enumerate(opt_config.variables):
        if var.re_plant == "pv":
            pv_step_mwdc = var.step
        if var.re_plant == "wind":
            wind_step_mw = var.step
    # if "battery" in re_plant_desc:
    #         include_battery = True
    # else:
    #     include_battery = False
    if "wind-pv" in re_plant_desc:
        wind_size_mw, pv_size_mwdc = res.x
        # pv_capacity_mwac = pv_size_mwdc/ned_man.dc_ac_ratio
    else:
        if "wind" in re_plant_desc:
            wind_size_mw = res.x[0]
            pv_size_mwdc = 0.0
            # pv_capacity_mwac = 0.0
            

        if "pv" in re_plant_desc:
            pv_size_mwdc = res.x[0]
            # pv_capacity_mwac = pv_size_mwdc/ned_man.dc_ac_ratio
            wind_size_mw = 0.0
    if wind_size_mw%wind_step_mw == 0:
        unique_wind_sizes = np.array([wind_size_mw])
    else:
        wind_lowerbound = wind_step_mw*np.floor(wind_size_mw/wind_step_mw)
        wind_upperbound = wind_step_mw*np.ceil(wind_size_mw/wind_step_mw)
        unique_wind_sizes = np.array([wind_lowerbound,wind_upperbound])
    if pv_size_mwdc%pv_step_mwdc == 0:
        unique_solar_sizes_dc = np.array([pv_size_mwdc])
    else:
        solar_lowerbound = pv_step_mwdc*np.floor(pv_size_mwdc/pv_step_mwdc)
        solar_upperbound = pv_step_mwdc*np.ceil(pv_size_mwdc/pv_step_mwdc)
        unique_solar_sizes_dc = np.array([solar_lowerbound,solar_upperbound])
    pv_sizes = np.tile(unique_solar_sizes_dc,len(unique_wind_sizes))
    wind_sizes = np.repeat(unique_wind_sizes,len(unique_solar_sizes_dc))
    
    return wind_sizes,pv_sizes

    
def get_wind_pv_initial_run_cases_list(opt_config:OptimizeConfig,ned_site:SiteSimplex):
    for i,var in enumerate(opt_config.variables):
        if var.re_plant == "pv":
            pv_sizes_mwdc = var.extra_simplex_sizes
        if var.re_plant == "wind":
            wind_sizes_mw = var.extra_simplex_sizes
    for di,design in enumerate(opt_config.optimization_design_list):
    
        simplex_for_design = ned_site.get_simplex_for_plant_design(design)
        if "wind" in design:
            wind_sizes_mw += list(np.unique(simplex_for_design["wind"].to_list()))
        if "pv" in design:
            pv_sizes_mwdc += list(np.unique(simplex_for_design["pv"].to_list()))
    
    unique_wind_sizes = np.unique(wind_sizes_mw)
    unique_pv_sizes_dc = np.unique(pv_sizes_mwdc)

    wind_sizes = []
    pv_sizes_mwdc = []
    for wi,wind in enumerate(unique_wind_sizes):
        for si,solar in enumerate(unique_pv_sizes_dc):
            if wind != 0 and solar != 0:
                wind_sizes += [wind]
                pv_sizes_mwdc += [solar]
    return wind_sizes,pv_sizes_mwdc



def make_optimization_config(optimization_config):
    optimization_design_list = optimization_config["optimization_cases"]
    design_vars = []
    for k in optimization_config["design_variables"].keys():
        if optimization_config["design_variables"][k]["flag"]:
            design_var = DesignVariable.from_dict(optimization_config["design_variables"][k])
            design_vars.append(design_var)

    merit_figure = list(optimization_config["merit_figures"].keys())
    optimization_params = optimization_config["driver"]["optimization"]
    simplex_design_case =  optimization_config["driver"]["design_of_simplex"]
    use_existing_ts = optimization_config["existing_timeseries_info"].pop("flag")
    opt_config = OptimizeConfig(
        variables=design_vars,
        optimization_design_list=optimization_design_list,
        merit_figures=merit_figure,
        simplex_design_case=simplex_design_case,
        optimization_params=optimization_params,
        use_existing_timeseries_info=use_existing_ts,
        existing_timeseries_data_info=optimization_config["existing_timeseries_info"])
    return opt_config
def update_hopp_costs_for_sizes(hopp_results,ned_man,wind_size_mw,solar_size_mwac,include_battery):
    #TODO: replace hopp_results["hybrid_plant"] with hybrid_plant
    pv_capacity_kwdc = solar_size_mwac*ned_man.dc_ac_ratio*1e3
    wind_capacity_kw = wind_size_mw*1e3
    if wind_size_mw>0:
        hopp_results["hybrid_plant"].wind.system_capacity_kw = wind_capacity_kw
    if pv_capacity_kwdc>0:
        hopp_results["hybrid_plant"].pv.system_capacity_kw = pv_capacity_kwdc
    if include_battery:
        hopp_results = int_tool.add_battery_to_hopp_results(hopp_results,ned_man)
        
    else:
        hopp_results = int_tool.remove_battery_from_hopp_results(hopp_results)
        

    hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[ned_man.baseline_atb_case])

    return hopp_results


def initialize_optimization_data(input_config,optimization_config):
    #TODO: update
    site_list, input_data = setup_runs(input_config)
    
    config_input_dict,ned_output_config_dict,ned_manager_dict = input_data
    if optimization_config["general"]["use_previous_run_results"]:
        
        initial_simplex = pd.DataFrame()
        for merit_figure in optimization_config["merit_figures"].keys():
            simplex_params = optimization_config["merit_figures"][merit_figure]["previous_results_simplex"]
        # simplex_params = optimization_config["driver"]["design_of_simplex"]
            simplex_sitelist_filename = "OffGridBaseline_SimplexSiteList_{}-{}-{}_{}-{}-{}.pkl".format(simplex_params["atb_scenario"],simplex_params["atb_year"],simplex_params["policy_scenario"],simplex_params["h2_storage_desc"],simplex_params["h2_storage_type"],simplex_params["h2_transport_desc"])
            simplex_sitelist_filepath = os.path.join(str(SITELIST_DIR),simplex_sitelist_filename)
            if os.path.isfile(simplex_sitelist_filepath):
                if ".pkl" in simplex_sitelist_filepath:
                    sitelist_simplex = pd.read_pickle(simplex_sitelist_filepath)
                else:
                    sitelist_simplex = pd.read_csv(simplex_sitelist_filepath)
            else:
                sitelist_simplex = make_sitelist_simplex_baseline_offgrid(**simplex_params)
            initial_simplex = pd.concat([initial_simplex,sitelist_simplex],axis=0)
    else:
        initial_simplex = None
    ned_manager_dict.update({"baseline_h2_storage_type": optimization_config["driver"]["design_of_simplex"]["h2_storage_type"]})
    ned_manager_dict.update({"baseline_atb_case": optimization_config["driver"]["design_of_simplex"]["atb_scenario"]})
    ned_manager_dict.update({"baseline_incentive_opt": int(optimization_config["driver"]["design_of_simplex"]["policy_scenario"])})
    return ned_manager_dict,config_input_dict,ned_output_config_dict,site_list,initial_simplex #sitelist_simplex

def initialize_site_for_run(site_info,site_simplex,ned_manager_dict,config_input_dict,ned_output_dict,optimization_config):
    #TODO: update for site_simplex
    ned_site = Site.from_dict(site_info)
    ned_output_dict.update({"site":ned_site})
    ned_output_dict.update({"extra_desc":"onsite_storage"})
    ned_out = NedOutputs.from_dict(ned_output_dict)
    ned_man = NedManager(**ned_manager_dict)
    config = GreenHeartSimulationConfig(**config_input_dict)
    # set renewable design info based on config stuff
    ned_man.set_renewable_specs(config)
    # check that greenheart config parameters are equal to stuff input in main.yaml file
    config = check_config_values(config,ned_man)
    ned_man.set_default_hopp_technologies(config.hopp_config["technologies"])
    # update lat and lon in hopp_config, update feedstock region in greenheart config
    config = update_config_for_site(
        ned_site=ned_site,
        config=config,
        )
    #update greenheart config for h2 storage situation and update costs for baseline case
    config = update_config_for_baseline_cases(
        ned_site=ned_site,
        config=config,
        ned_man = ned_man,
        )
    hopp_site = SiteInfo(**config.hopp_config["site"])
    
    #TODO: UPDATE STUFF FROM BELOW
    if site_simplex is not None:
        site_info.update({"initial_simplex_data":site_simplex})
    # site_info.update({"simplex_case_info":optimization_config["driver"]["design_of_simplex"]})
    site_info.update({"design_variables_info":optimization_config["design_variables"]})
    site_info.update({"merit_figures":list(optimization_config["merit_figures"].keys())})
    # site_info.update({"simplex_data":site_simplex})
    # site_info.update({"simplex_case_info":optimization_config["driver"]["design_of_simplex"]})
    # site_info.update({"design_variables_info":optimization_config["design_variables"]})
    # site_info.update({"merit_figure":optimization_config["merit_figure"]})
    ned_site = SiteSimplex.from_dict(site_info)
    return hopp_site,ned_site,ned_man,ned_out,config

def get_simplex_for_bound_cases(hopp_site:SiteInfo,ned_site:SiteSimplex,ned_man:NedManager,ned_out:NedOutputs,config:GreenHeartSimulationConfig,run_fast=True):
    n_decimals = 1
    n_turbs_max = ned_site.design_variables["wind"]["upper"]//ned_site.design_variables["wind"]["step"]
    max_wind_capacity_mw = n_turbs_max*ned_site.design_variables["wind"]["step"]
    n_turbs_min = ned_site.design_variables["wind"]["lower"]//ned_site.design_variables["wind"]["step"]
    min_wind_capacity_mw = n_turbs_min*ned_site.design_variables["wind"]["step"]

    n_panels_max = ned_site.design_variables["pv"]["upper"]//ned_site.design_variables["pv"]["step"]
    max_pv_capacity_mw = n_panels_max*ned_site.design_variables["pv"]["step"]
    n_panels_min = ned_site.design_variables["pv"]["lower"]//ned_site.design_variables["pv"]["step"]
    min_pv_capacity_mw = n_panels_min*ned_site.design_variables["pv"]["step"]
    
    if "dc" in ned_site.design_variables["pv"]["units"].lower():
        # convert to mwac
        max_pv_capacity_mw = max_pv_capacity_mw/ned_man.dc_ac_ratio
        min_pv_capacity_mw = min_pv_capacity_mw/ned_man.dc_ac_ratio

    unique_wind_sizes_mw = np.array([min_wind_capacity_mw,max_wind_capacity_mw])
    unique_pv_sizes_mw = np.array([min_pv_capacity_mw,max_pv_capacity_mw])
    unique_descriptions = ["lower","upper"]
    simplex_res = pd.DataFrame()
    simplex_keys = ["wind_size_mw","pv_size_mwdc","battery","lcoh"]
    cnt = 0
    hopp_res_tracker = []
    if run_fast:
        generation_profile_dict = {}
        for i in range(len(unique_wind_sizes_mw)):
            wind_capacity_mw = unique_wind_sizes_mw[i]
            pv_capacity_mwac = unique_pv_sizes_mw[i]
            include_battery = False
            lcoh, hopp_results, electrolyzer_physics_results = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_capacity_mw,pv_capacity_mwac,include_battery,output_level=2,save_detailed_results=True)
            hopp_res_tracker.append(hopp_results)
            simplex_vals = [wind_capacity_mw,pv_capacity_mwac*ned_man.dc_ac_ratio,include_battery,lcoh]
            temp_df = pd.DataFrame(simplex_vals,index=simplex_keys,columns=[cnt]).T
            simplex_res = pd.concat([simplex_res,temp_df],axis=0)
            cnt+=1
            wind_profile_kw = np.array(hopp_results["hybrid_plant"].wind.generation_profile)
            pv_profile_kwac = np.array(hopp_results["hybrid_plant"].pv.generation_profile)
            # generation_profile_dict.update({"wind-{}".format(unique_descriptions[i]):wind_profile_kw})
            # generation_profile_dict.update({"pv-{}".format(unique_descriptions[i]):pv_profile_kwac})
            generation_profile_dict.update({"wind-{}".format(round(wind_capacity_mw,n_decimals)):wind_profile_kw})
            pv_gen_size_dc = round(pv_capacity_mwac*ned_man.dc_ac_ratio,n_decimals)
            generation_profile_dict.update({"pv-{}".format(pv_gen_size_dc):pv_profile_kwac})

    
    # hopp_results["combined_hybrid_power_production_hopp"]


    wind_sizes = np.repeat(unique_wind_sizes_mw,2)
    pv_sizes = np.tile(unique_pv_sizes_mw,2)
    pv_sizes = np.concatenate((pv_sizes,np.zeros(2)))
    pv_sizes = np.concatenate((unique_pv_sizes_mw,pv_sizes))
    wind_sizes = np.concatenate((np.zeros(2),wind_sizes))
    wind_sizes = np.concatenate((wind_sizes,unique_wind_sizes_mw))
    n_gen_runs = len(wind_sizes)
    battery_cases = [False]*n_gen_runs #+ [True]*n_gen_runs
    # wind_sizes = np.repeat(wind_sizes,2)
    # pv_sizes = np.repeat(pv_sizes,2)

    
    for i in range(len(wind_sizes)):
        wind_capacity_mw = round(wind_sizes[i],n_decimals)
        pv_capacity_mwac = pv_sizes[i]
        include_battery = battery_cases[i]
        pv_capacity_mwdc = round(pv_capacity_mwac*ned_man.dc_ac_ratio,n_decimals)
        # if run_fast:
        if wind_capacity_mw==0:
            wind_power = np.zeros(8760)
        else:
            wind_power = generation_profile_dict["wind-{}".format(wind_capacity_mw)]
        if pv_capacity_mwac == 0:
            pv_power = np.zeros(8760)
        else:
            pv_power = generation_profile_dict["pv-{}".format(pv_capacity_mwdc)]
        hopp_results = update_hopp_costs_for_sizes(hopp_results,ned_man,wind_capacity_mw,pv_capacity_mwac,include_battery)
        hopp_results["combined_hybrid_power_production_hopp"] =  wind_power + pv_power
        hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[ned_man.baseline_atb_case])

        lcoh, ned_out = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_capacity_mw,pv_capacity_mwac,include_battery,output_level=4,hopp_results=hopp_results)
        # else:
        #     lcoh, ned_out = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_capacity_mw,pv_capacity_mwac,include_battery,output_level=4)
        simplex_vals = [wind_capacity_mw,pv_capacity_mwdc,include_battery,lcoh]
        temp_df = pd.DataFrame(simplex_vals,index=simplex_keys,columns=[cnt]).T
        simplex_res = pd.concat([simplex_res,temp_df],axis=0)
        cnt +=1
        []
        
    return simplex_res,generation_profile_dict,hopp_res_tracker[0]


def make_hopp_results_for_saved_generation(wind_size_mw:float,pv_size_mwdc:float,hopp_site:SiteInfo,ned_man:NedManager,config:GreenHeartSimulationConfig,REgen: RenewableGenerationTracker):
    # NOTE: this wont do the right stuff for battery!
    run_solar = False
    run_wind = False
    gen_keys = list(REgen.generation_profiles.keys())
    if pv_size_mwdc>0:
        pv_gen_keys = [k for k in gen_keys if "pv" in k]
        pv_gen_capacities = [round(float(k.split("-")[-1]),1) for k in pv_gen_keys]
        if round(pv_size_mwdc,1) in pv_gen_capacities:
            solar_power = REgen.generation_profiles["pv-{}".format(round(pv_size_mwdc,1))]
        else:
            run_solar = True
            pv_size_mwac = pv_size_mwdc/ned_man.dc_ac_ratio
            

    else:
        solar_power = np.zeros(8760)
    if wind_size_mw>0:
        wind_gen_keys = [k for k in gen_keys if "wind" in k]
        wind_gen_capacities = [round(float(k.split("-")[-1]),1) for k in wind_gen_keys]
        if round(wind_size_mw,1) in wind_gen_capacities:
            wind_power = REgen.generation_profiles["wind-{}".format(round(wind_size_mw,1))]
        else:
            run_wind = True
    else:
        wind_power = np.zeros(8760)
    
    if not run_wind and not run_solar:
        # dont need to run either
        # print("1")
        pv_size_mwac = pv_size_mwdc/ned_man.dc_ac_ratio
        # hopp_results = copy.deepcopy(REgen.example_hopp_results)
        hopp_results = update_hopp_costs_for_sizes(REgen.example_hopp_results,ned_man,wind_size_mw,pv_size_mwac,include_battery=False)
        hopp_results["combined_hybrid_power_production_hopp"] = wind_power + solar_power
        hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[ned_man.baseline_atb_case])
        #added below
        REgen.example_hopp_results["hybrid_plant"].wind = hopp_results["hybrid_plant"].wind
        REgen.example_hopp_results["hybrid_plant"].pv = hopp_results["hybrid_plant"].pv

    elif not run_wind and run_solar:
        # only need to run solar
        # print("2")
        hopp_config = copy.deepcopy(config.hopp_config)
        hopp_config = update_renewable_plant_design(ned_man,hopp_config,0,pv_size_mwac,include_battery=False,hopp_site_main=hopp_site)
        config.hopp_config = hopp_config
        config,hi,wind_cost_results, hopp_results = gh_mgmt.set_up_greenheart_run_renewables(config,power_for_peripherals_kw=0.0)
        hopp_results["hybrid_plant"].wind = REgen.ex_wind_plant #new
        hopp_results = update_hopp_costs_for_sizes(hopp_results,ned_man,0,pv_size_mwac,include_battery=False)
        solar_power = np.array(hopp_results["hybrid_plant"].pv.generation_profile)
        hopp_results["combined_hybrid_power_production_hopp"] =  wind_power + solar_power
        hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[ned_man.baseline_atb_case])
        REgen.add_generation_profile(hopp_results,0,pv_size_mwdc)
        #added below
        REgen.example_hopp_results["hybrid_plant"].pv = hopp_results["hybrid_plant"].pv

    elif not run_solar and run_wind:
        # print("3")
        # only need to run wind
        hopp_config = copy.deepcopy(config.hopp_config)
        hopp_config = update_renewable_plant_design(ned_man,hopp_config,wind_size_mw,0,include_battery=False,hopp_site_main=hopp_site)
        config.hopp_config = hopp_config
        config,hi,wind_cost_results, hopp_results = gh_mgmt.set_up_greenheart_run_renewables(config,power_for_peripherals_kw=0.0)
        hopp_results["hybrid_plant"].pv = REgen.ex_pv_plant #new
        # hopp_results["hybrid_plant"].pv.generation_profile = solar_power #new
        hopp_results = update_hopp_costs_for_sizes(hopp_results,ned_man,wind_size_mw,0,include_battery=False)
        wind_power = np.array(hopp_results["hybrid_plant"].wind.generation_profile)
        hopp_results["combined_hybrid_power_production_hopp"] =  wind_power + solar_power
        hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[ned_man.baseline_atb_case])
        REgen.add_generation_profile(hopp_results,wind_size_mw,0)
        #added below
        REgen.example_hopp_results["hybrid_plant"].wind = hopp_results["hybrid_plant"].wind

    elif run_solar and run_wind:
        # need to run both
        # print("4")
        hopp_config = copy.deepcopy(config.hopp_config)
        hopp_config = update_renewable_plant_design(ned_man,hopp_config,wind_size_mw,pv_size_mwac,include_battery=False,hopp_site_main=hopp_site)
        config.hopp_config = hopp_config
        config,hi,wind_cost_results, hopp_results = gh_mgmt.set_up_greenheart_run_renewables(config,power_for_peripherals_kw=0.0)
        hopp_results = update_hopp_costs_for_sizes(hopp_results,ned_man,wind_size_mw,pv_size_mwac,include_battery=False)
        solar_power = np.array(hopp_results["hybrid_plant"].pv.generation_profile)
        wind_power = np.array(hopp_results["hybrid_plant"].wind.generation_profile)
        hopp_results["combined_hybrid_power_production_hopp"] =  wind_power + solar_power
        hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[ned_man.baseline_atb_case])
        REgen.add_generation_profile(hopp_results,round(wind_size_mw,1),round(pv_size_mwdc,1))
        #added below
        REgen.example_hopp_results["hybrid_plant"].wind = hopp_results["hybrid_plant"].wind
        REgen.example_hopp_results["hybrid_plant"].pv = hopp_results["hybrid_plant"].pv
    REgen.example_hopp_results["hybrid_plant"].wind._system_model
    hopp_results["hybrid_plant"].wind._system_model
    return hopp_results,REgen


def run_unique_wind_solar_sizes(wind_sizes,pv_sizes_mwdc,ned_out,ned_man,config,hopp_site,include_battery = False):
    n_decimals = 1
    
    # if "dc" in ned_site.design_variables["pv"]["units"].lower():
    #     # convert to mwac
    #     max_pv_capacity_mw = max_pv_capacity_mw/ned_man.dc_ac_ratio
    #     min_pv_capacity_mw = min_pv_capacity_mw/ned_man.dc_ac_ratio

    unique_wind_sizes_mw = np.unique(wind_sizes)
    unique_pv_sizes_mw = np.unique(pv_sizes_mwdc)
    # print("wind sizes: {}".format(unique_wind_sizes_mw))
    # print("pv sizes: {}".format(unique_pv_sizes_mw))
    if len(unique_pv_sizes_mw) != len(unique_wind_sizes_mw):
        if len(unique_pv_sizes_mw)>len(unique_wind_sizes_mw):
            # more unique pv sizes than wind
            n_extra_wind = len(unique_pv_sizes_mw) - len(unique_wind_sizes_mw)
            unique_wind_sizes_mw = np.concatenate([unique_wind_sizes_mw,np.min(unique_wind_sizes_mw)*np.ones(n_extra_wind)],axis=0)
            
        else:
            # more unique wind sizes than pv
            n_extra_pv = len(unique_wind_sizes_mw) - len(unique_pv_sizes_mw)
            unique_pv_sizes_mw = np.concatenate([unique_pv_sizes_mw,np.min(unique_pv_sizes_mw)*np.ones(n_extra_pv)],axis=0)
    
    simplex_res = pd.DataFrame()
    simplex_keys = ["wind_size_mw","pv_size_mwdc","battery","lcoh"]
    cnt = 0
    hopp_res_tracker = []
    
    generation_profile_dict = {}
    for i in range(len(unique_wind_sizes_mw)):
        # print("running {} of {}".format(i,len(unique_wind_sizes_mw)))
        
        wind_capacity_mw = unique_wind_sizes_mw[i]
        pv_capacity_mwdc = unique_pv_sizes_mw[i]
        pv_capacity_mwac = pv_capacity_mwdc/ned_man.dc_ac_ratio
        
        # print("wind: {} MW | solar {} MWdc".format(wind_capacity_mw,pv_capacity_mwdc))
        lcoh, hopp_results, electrolyzer_physics_results = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_capacity_mw,pv_capacity_mwac,include_battery,output_level=2,save_detailed_results=True)
        hopp_res_tracker.append(hopp_results)
        simplex_vals = [wind_capacity_mw,pv_capacity_mwdc,include_battery,lcoh]
        temp_df = pd.DataFrame(simplex_vals,index=simplex_keys,columns=[cnt]).T
        simplex_res = pd.concat([simplex_res,temp_df],axis=0)
        cnt+=1
        if wind_capacity_mw>0:
            wind_profile_kw = np.array(hopp_results["hybrid_plant"].wind.generation_profile)
        else:
            wind_profile_kw = np.zeros(8760)
        if pv_capacity_mwdc>0:
            pv_profile_kwac = np.array(hopp_results["hybrid_plant"].pv.generation_profile)
        else:
            pv_profile_kwac = np.zeros(8760)
        generation_profile_dict.update({"wind-{}".format(round(wind_capacity_mw,n_decimals)):wind_profile_kw})
        pv_gen_size_dc = round(pv_capacity_mwdc,n_decimals)
        generation_profile_dict.update({"pv-{}".format(round(pv_gen_size_dc,n_decimals)):pv_profile_kwac})

    # print("finished running generation")
    for i in range(len(wind_sizes)):
        # print("running combo design {} of {}".format(i,len(wind_sizes)))
        wind_capacity_mw = round(wind_sizes[i],n_decimals)
        pv_capacity_mwdc = round(pv_sizes_mwdc[i],n_decimals)
        pv_capacity_mwac = pv_capacity_mwdc/ned_man.dc_ac_ratio
        # print("wind: {} MW | solar {} MWdc".format(wind_capacity_mw,pv_capacity_mwdc))
        # if run_fast:
        if wind_capacity_mw==0:
            wind_power = np.zeros(8760)
        else:
            wind_power = generation_profile_dict["wind-{}".format(wind_capacity_mw)]
        if pv_capacity_mwdc == 0:
            pv_power = np.zeros(8760)
        else:
            pv_power = generation_profile_dict["pv-{}".format(pv_capacity_mwdc)]
        hopp_results = update_hopp_costs_for_sizes(hopp_results,ned_man,wind_capacity_mw,pv_capacity_mwac,include_battery)
        hopp_results["combined_hybrid_power_production_hopp"] =  wind_power + pv_power
        hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[ned_man.baseline_atb_case])

        lcoh, ned_out = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_capacity_mw,pv_capacity_mwac,include_battery,output_level=4,hopp_results=hopp_results)
        # else:
        #     lcoh, ned_out = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_capacity_mw,pv_capacity_mwac,include_battery,output_level=4)
        simplex_vals = [wind_capacity_mw,pv_capacity_mwdc,include_battery,lcoh]
        temp_df = pd.DataFrame(simplex_vals,index=simplex_keys,columns=[cnt]).T
        simplex_res = pd.concat([simplex_res,temp_df],axis=0)
        cnt +=1
        []
        
    return simplex_res #,generation_profile_dict,hopp_res_tracker[0]


    # hopp_config = copy.deepcopy(config.hopp_config)
    # hopp_config = update_renewable_plant_design(ned_man,hopp_config,wind_capacity_mw,pv_size_mwac,include_battery=False,hopp_site_main=hopp_site)
    # config.hopp_config = hopp_config
    # config,hi,wind_cost_results, hopp_results = gh_mgmt.set_up_greenheart_run_renewables(config,power_for_peripherals_kw=0.0)
# def find_next_sizes_to_run(ned_site:SiteSimplex,re_plant_desc:str):
#     ned_site.full_simplex.loc[re_plant_desc].sort_values(ned_site.merit_figure,ascending=True)
# def get_simplex_for_best_cases(hopp_site:SiteInfo,ned_site:SiteSimplex,ned_man:NedManager,ned_out:NedOutputs,config:GreenHeartSimulationConfig,re_plant_desc:str):
#     n = len(re_plant_desc.replace("-battery","").split("-"))
#     simplex = ned_site.full_simplex.loc[re_plant_desc].sort_values(ned_site.merit_figure,ascending=True).iloc[:n+1]
#     x,c = ned_site.get_final_simplex_for_plant(re_plant_desc)
#     y = np.array(simplex[ned_site.merit_figure].to_list())
#     dx = np.diff(x,axis=0)
#     dy = np.diff(y)
#     x[0] - dx[0]/2

#     if n==2:
#         ned_site.full_simplex.loc["wind-pv"].sort_values("wind",ascending=False)

#         xw = simplex["wind"].to_list()[::-1]
#         xs = simplex["pv"].to_list()[::-1]
#         y = simplex[ned_site.merit_figure].to_list()[::-1]
#         dxw = np.diff(xw)
#         dxs = np.diff(xs)
#         dy = np.diff(dy)

        
#     elif n==1:
#         x = simplex[re_plant_desc.replace("-battery","")].to_list()[::-1]
#         y = simplex[ned_site.merit_figure].to_list()[::-1]
#         dx = np.diff(x)
#         dy = np.diff(y)
#         alpha_k = (dx*dx)/(dx*dy)
#         x_next = x[0] - (alpha_k*y[0])



# if __name__=="__main__":
#     atb_year = 2030
#     input_filepath = INPUT_DIR/"v1-optimize-offgrid/main-{}.yaml".format(atb_year)
#     optimization_filepath = INPUT_DIR/"v1-optimize-offgrid/optimize_config.yaml"
#     input_config = load_yaml(input_filepath)

#     input_config["hpc_or_local"] = "local"
#     input_config["renewable_resource_origin"] = "API"
#     if "env_path" in input_config:
#         input_config.pop("env_path")

#     optimization_config = load_yaml(optimization_filepath)
#     site_id = 1
#     ned_manager_dict,config_input_dict,ned_output_config_dict,site_list,sitelist_simplex = initialize_optimization_data(input_config,optimization_config)
#     site_info = site_list.loc[site_id].to_dict()
#     site_simplex = sitelist_simplex.loc[site_id]
#     hopp_site,ned_site,ned_man,ned_out,config = initialize_site_for_run(site_info,site_simplex,ned_manager_dict,config_input_dict,ned_output_config_dict,optimization_config)
#     ned_site.get_simplex_for_plant_design("wind")
#     ned_site.get_inputs_for_optimization("wind-pv")
#     []

