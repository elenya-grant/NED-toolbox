
from toolbox.simulation.ned_site import Site, NedManager
from toolbox import SITELIST_DIR,LIB_DIR,ROOT_DIR, INPUT_DIR
import pandas as pd
import yaml
import os
import time
from yamlinclude import YamlIncludeConstructor
from pathlib import Path
from greenheart.simulation.greenheart_simulation import GreenHeartSimulationConfig
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=LIB_DIR
)
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=LIB_DIR / "greenheart_hopp_config/"
)
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=LIB_DIR / "pv"
)
from toolbox.utilities.file_tools import check_create_folder
from hopp.utilities import load_yaml
from hopp.utilities.utilities import write_yaml
import toolbox.simulation.greenheart_management as gh_mgmt
import toolbox.tools.interface_tools as int_tool
import copy
import greenheart.tools.eco.hydrogen_mgmt as he_h2
from toolbox.simulation.results import NedOutputs #, FinanceResults,PhysicsResults

from toolbox.utilities.ned_logger import toolbox_logger as t_log

def run_lcoh_lcoe(
    ned_out: NedOutputs,
    config:GreenHeartSimulationConfig,
    re_plant_desc,
    atb_cost_case,
    hopp_results,
    capex_breakdown,
    opex_breakdown_annual,
    wind_cost_results,
    electrolyzer_physics_results,
    total_accessory_power_renewable_kw,
    total_accessory_power_grid_kw = 0.0,
    calc_lcoe = True,
    calc_lcoh = True,
    ):
    t_log.info("\t{} Plant".format(re_plant_desc))
    t_log.info("\t{} ATB Cost Case".format(atb_cost_case))
    t_log.info("\t{} H2 Storage".format(config.greenheart_config["h2_storage"]["type"]))
    t_log.info("tax incentive {}".format(config.incentive_option))
    if calc_lcoe:
        lcoe, pf_lcoe, lcoe_res = gh_mgmt.calc_lcoe(
                    hopp_results,
                    capex_breakdown,
                    opex_breakdown_annual,
                    wind_cost_results,
                    config)
        lcoe_res.update_atb_scenario(atb_scenario=atb_cost_case)
        lcoe_res.update_re_plant_type(re_plant_type=re_plant_desc)
        ned_out.add_LCOE_Results(lcoe_res)
        t_log.info("\t\tLCOE: \t${}/MWh".format(round(lcoe*1e3,2)))
    if calc_lcoh:
        lcoh, pf_lcoh, lcoh_res = gh_mgmt.calc_offgrid_lcoh(
            hopp_results,
            capex_breakdown,
            opex_breakdown_annual,
            wind_cost_results,
            electrolyzer_physics_results,
            total_accessory_power_renewable_kw,
            total_accessory_power_grid_kw,
            config
            )
        lcoh_res.update_atb_scenario(atb_scenario=atb_cost_case)
        lcoh_res.update_re_plant_type(re_plant_type=re_plant_desc)
        ned_out.add_LCOH_Results(lcoh_res)
        
        t_log.info("\t\tLCOH: \t${}/kg".format(round(lcoh,3)))
    return ned_out


def sweep_policy_cases(
    ned_out: NedOutputs,
    config:GreenHeartSimulationConfig,
    re_plant_desc,
    atb_cost_case,
    hopp_results,
    capex_breakdown,
    opex_breakdown_annual,
    wind_cost_results,
    electrolyzer_physics_results,
    total_accessory_power_renewable_kw,
    total_accessory_power_grid_kw,
    calc_lcoe,
    calc_lcoh,
    ):
    
    
    incentives_list = list(config.greenheart_config["policy_parameters"].keys())
    #don't repeat incentive that would'ce already been run
    incentives_list = [k for k in incentives_list if k.split("option")[-1] != str(config.incentive_option)]
    for incentive_key in incentives_list:
        # t_log.info("tax incentive: {}".format(incentive_key))
        incentive_num = int(incentive_key.split("option")[-1])
        config.incentive_option = incentive_num
        ned_out = run_lcoh_lcoe(
            ned_out,
            config,
            re_plant_desc,
            atb_cost_case,
            hopp_results,
            capex_breakdown,
            opex_breakdown_annual,
            wind_cost_results,
            electrolyzer_physics_results,
            total_accessory_power_renewable_kw,
            total_accessory_power_grid_kw = total_accessory_power_grid_kw,
            calc_lcoe = calc_lcoe,
            calc_lcoh = calc_lcoh,
            )
        
    return ned_out

def run_costs_for_different_h2_storage_type(
    ned_site:Site,
    config:GreenHeartSimulationConfig,
    ned_man: NedManager,
    ned_out: NedOutputs,
    new_h2_storage_type,
    re_plant_desc,
    atb_cost_case,
    hopp_results, 
    electrolyzer_physics_results,
    h2_prod_store_results, 
    h2_transport_results, 
    offshore_component_results, 
    total_accessory_power_renewable_kw,
    wind_cost_results,
    total_accessory_power_grid_kw,
    sweep_incentives = True,

):  
    t_log.info("H2 storage type: {}".format(new_h2_storage_type))
    h2_storage_type_id = [k for k in list(ned_man.h2_system_types.keys()) if ned_man.h2_system_types[k]["h2_storage_type"] == new_h2_storage_type]
    plant_design_id = ned_man.h2_system_types[h2_storage_type_id[0]]["plant_design_num"]
    
    config.greenheart_config["h2_storage"].update({"type":new_h2_storage_type})
    config.plant_design_scenario = int(plant_design_id)
    config.design_scenario = config.greenheart_config["plant_design"]["scenario{}".format(plant_design_id)]

    if ned_man.h2_system_types[h2_storage_type_id[0]]["distance_to_storage_key"] is None:
        distance = 0
        config.greenheart_config["site"]["distance_to_storage_km"] = 0
    else:
        distance = ned_site.__getattribute__(ned_man.h2_system_types[h2_storage_type_id[0]]["distance_to_storage_key"])
        config.greenheart_config["site"]["distance_to_storage_km"] = distance
        orbit_config = {"site":{"distance_to_landfall":distance}}
        h2_transport_results[2] = he_h2.run_h2_transport_pipe(
            orbit_config,
            config.greenheart_config,
            electrolyzer_physics_results,
            config.design_scenario,
            verbose = False)
        h2_transport_results[2] 
        # h2_transport_results = [h2_pipe_array_results, h2_transport_compressor_results, h2_transport_pipe_results]
    config.greenheart_config["site"]["distance_to_storage_km"] = distance
    # electrolyzer_cost_results, h2_storage_results = h2_prod_store_results
    pipe_storage, h2_storage_results = he_h2.run_h2_storage(
            config.hopp_config,
            config.greenheart_config,
            config.turbine_config,
            electrolyzer_physics_results,
            config.design_scenario,
            verbose=False,
        )
    h2_prod_store_results[1] = h2_storage_results
    capex_breakdown, opex_breakdown_annual, fin_res = gh_mgmt.calc_capex_and_opex(
            hopp_results, 
            h2_prod_store_results, 
            h2_transport_results, 
            offshore_component_results, 
            config
            )
    fin_res.update_atb_scenario(atb_cost_case)
    fin_res.update_re_plant_type(re_plant_desc)
    ned_out.add_Finance_Results(fin_res)
    ned_out = run_lcoh_lcoe(
            ned_out,
            config,
            re_plant_desc,
            atb_cost_case,
            hopp_results,
            capex_breakdown,
            opex_breakdown_annual,
            wind_cost_results,
            electrolyzer_physics_results,
            total_accessory_power_renewable_kw,
            total_accessory_power_grid_kw = total_accessory_power_grid_kw,
            calc_lcoe = False,
            calc_lcoh = True,
        )
    if sweep_incentives:
        ned_out = sweep_policy_cases(
                ned_out,
                config,
                re_plant_desc,
                atb_cost_case,
                hopp_results,
                capex_breakdown,
                opex_breakdown_annual,
                wind_cost_results,
                electrolyzer_physics_results,
                total_accessory_power_renewable_kw,
                total_accessory_power_grid_kw = total_accessory_power_grid_kw,
                calc_lcoe = False,
                calc_lcoh = True,
                )
    #doesnt require different ancillary power usage, just changes h2 storage cost
    return ned_out


def sweep_atb_cost_cases(
    ned_site: Site,
    ned_man: NedManager,
    ned_out: NedOutputs,
    re_plant_desc,
    hopp_results, 
    electrolyzer_physics_results,
    h2_prod_store_results, 
    h2_transport_results, 
    offshore_component_results, 
    config:GreenHeartSimulationConfig,
    total_accessory_power_renewable_kw,
    wind_cost_results,
    total_accessory_power_grid_kw,
    sweep_incentives = True,
    new_h2_storage_type = None,
    ):
    for atb_cost_case in ned_man.atb_cases_desc:
        t_log.info("\t{} ATB Cost Case".format(atb_cost_case))
        hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[atb_cost_case])
        electrolyzer_cost_results = gh_mgmt.update_electrolysis_costs(config.greenheart_config,electrolyzer_physics_results,ned_man.atb_cost_cases_electrolyzer[atb_cost_case])
        h2_prod_store_results[0] = electrolyzer_cost_results
        capex_breakdown, opex_breakdown_annual, fin_res = gh_mgmt.calc_capex_and_opex(
            hopp_results, 
            h2_prod_store_results, 
            h2_transport_results, 
            offshore_component_results, 
            config
            )
        fin_res.update_atb_scenario(atb_cost_case)
        fin_res.update_re_plant_type(re_plant_desc)
        ned_out.add_Finance_Results(fin_res)
        ned_out = run_lcoh_lcoe(
            ned_out,
            config,
            re_plant_desc,
            atb_cost_case,
            hopp_results,
            capex_breakdown,
            opex_breakdown_annual,
            wind_cost_results,
            electrolyzer_physics_results,
            total_accessory_power_renewable_kw,
            total_accessory_power_grid_kw = total_accessory_power_grid_kw,
            calc_lcoe = True,
            calc_lcoh = True,
        )
        if sweep_incentives:
            ned_out = sweep_policy_cases(
                ned_out,
                config,
                re_plant_desc,
                atb_cost_case,
                hopp_results,
                capex_breakdown,
                opex_breakdown_annual,
                wind_cost_results,
                electrolyzer_physics_results,
                total_accessory_power_renewable_kw,
                total_accessory_power_grid_kw = total_accessory_power_grid_kw,
                calc_lcoe = True,
                calc_lcoh = True,
                )

        if isinstance(new_h2_storage_type,str):
            ned_out = run_costs_for_different_h2_storage_type(
                ned_site,
                config,
                ned_man,
                ned_out,
                new_h2_storage_type,
                re_plant_desc,
                atb_cost_case,
                hopp_results, 
                electrolyzer_physics_results,
                h2_prod_store_results, 
                h2_transport_results, 
                offshore_component_results, 
                total_accessory_power_renewable_kw,
                wind_cost_results,
                total_accessory_power_grid_kw = total_accessory_power_grid_kw,
                sweep_incentives = sweep_incentives
                )
            
    return ned_out


def sweep_plant_design_types(
    ned_site:Site,
    config:GreenHeartSimulationConfig,
    ned_man: NedManager,
    ned_out: NedOutputs,
    ):
    total_accessory_power_grid_kw = 0.0 #always zero for non-pressurized storage
    start = time.perf_counter()
    t_log.info("({},{}) --- {},{}".format(ned_site.latitude,ned_site.longitude,ned_site.state,ned_site.county))
    
    if ned_man.baseline_h2_storage_type == "none":
        next_h2_storage_type = "pipe"
    elif ned_man.baseline_h2_storage_type == "pipe":
        next_h2_storage_type = "none"
    elif ned_man.baseline_h2_storage_type == "lined_rock_cavern":
        next_h2_storage_type = "salt_cavern"
    elif ned_man.baseline_h2_storage_type == "salt_cavern":
        next_h2_storage_type = "lined_rock_cavern"
    renewable_plant_capacity_MWac = ned_man.electrolyzer_size_mw*ned_man.re_plant_capacity_multiplier
    if ned_man.re_plant_capacity_multiplier<1:
        # grid_min_size_kw = renewable_plant_capacity_MWac*1e3
        #in hopp_mangement, grid_interconnect_kw is set to power_for_peripherals_kw + electrolyzer_rating*1e3
        #in this case, we want grid_interconnect_kw = wind_rating_kw + pv_rating_kw + power_for_peripherals_kw
        adjustment_ancillary_power_usage_kw = renewable_plant_capacity_MWac - ned_man.electrolyzer_size_mw
    else:
        #in hopp_mangement, grid_interconnect_kw is set to power_for_peripherals_kw + electrolyzer_rating*1e3
        # grid_min_size_kw = ned_man.electrolyzer_size_mw*1e3
        adjustment_ancillary_power_usage_kw = 0

    t_log.info("renewable plant generation capacity: {} MW-AC".format(renewable_plant_capacity_MWac))

    for plant_desc, gen_mult in ned_man.re_plant_types.items():
        t_log.info("plant-type: {}".format(plant_desc))
        print("----- {} ------".format(plant_desc))
        hopp_config = copy.deepcopy(config.hopp_config)
       
        if "wind" in plant_desc:
            wind_capacity_mw = gen_mult*renewable_plant_capacity_MWac
        else:
            wind_capacity_mw = 0

        if "pv" in plant_desc:
            pv_capacity_mwac = gen_mult*renewable_plant_capacity_MWac
        else:
            pv_capacity_mwac = 0
            
        if "battery" in plant_desc:
            include_battery = True
        else:
            include_battery = False

        print("wind capacity: {} MW".format(wind_capacity_mw))
        print("solar capacity: {} MWac".format(pv_capacity_mwac))
        hopp_config = int_tool.update_hopp_config_for_wind_capacity(wind_capacity_mw,ned_man,hopp_config)
        hopp_config = int_tool.update_hopp_config_for_solar_capacity(pv_capacity_mwac,ned_man,hopp_config)
        hopp_config = int_tool.update_hopp_config_for_battery(include_battery,ned_man,hopp_config)
        config.hopp_config = hopp_config
        ancillary_power_usage_kw = gh_mgmt.estimate_power_for_peripherals_kw_land_based(config.greenheart_config,renewable_plant_capacity_MWac*1e3,config.design_scenario)
        # below is done in hopp_mgmt.setup_hopp
        ancillary_power_for_grid_sizing_and_battery = ancillary_power_usage_kw + adjustment_ancillary_power_usage_kw
        # hopp_config["technologies"]["grid"]["interconnect_kw"] = grid_min_size_kw + ancillary_power_usage_kw
        config,hi,wind_cost_results, hopp_results = gh_mgmt.set_up_greenheart_run_renewables(config,power_for_peripherals_kw=ancillary_power_for_grid_sizing_and_battery)
        print("max power production: {}".format(max(hopp_results["combined_hybrid_power_production_hopp"])))
        ghg_res = gh_mgmt.run_physics_and_design(
            hopp_results = hopp_results,
            wind_cost_results = wind_cost_results,
            design_scenario = config.design_scenario,
            orbit_config = config.orbit_config,
            hopp_config = config.hopp_config,
            greenheart_config = config.greenheart_config,
            turbine_config = config.turbine_config,
            power_for_peripherals_kw_in=ancillary_power_usage_kw)
        phys_res, electrolyzer_physics_results, hopp_results,h2_prod_store_results, h2_transport_results,offshore_component_results,total_accessory_power_renewable_kw = ghg_res
        
        phys_res.update_re_plant_type(re_plant_type=plant_desc)
        # phys_res.update_h2_design_scenario(h2_storage_type=[],h2_transport_type)
        ned_out.add_Physics_Results(phys_res)

        ned_out = sweep_atb_cost_cases(
            ned_site,
            ned_man,
            ned_out,
            plant_desc,
            hopp_results, 
            electrolyzer_physics_results,
            h2_prod_store_results, 
            h2_transport_results, 
            offshore_component_results, 
            config,
            total_accessory_power_renewable_kw,
            wind_cost_results,
            total_accessory_power_grid_kw = total_accessory_power_grid_kw,
            sweep_incentives = True,
            new_h2_storage_type = next_h2_storage_type)

    end = time.perf_counter()
    t_log.info("{} min to run sim".format(round((end-start)/60,3)))
    return ned_out
       
def update_config_for_baseline_cases(
    ned_site:Site,
    config:GreenHeartSimulationConfig,
    ned_man:NedManager):
    #update baseline costs
    config.hopp_config["config"]["cost_info"] = ned_man.atb_cost_cases_hopp[ned_man.baseline_atb_case]
    config.greenheart_config["electrolyzer"].update(ned_man.atb_cost_cases_electrolyzer[ned_man.baseline_atb_case])
    # update baseline incentive option
    config.incentive_option = ned_man.baseline_incentive_opt
    # update params for baseline h2 storage system design case
    h2_design_key = [i for i in ned_man.h2_system_types.keys() if ned_man.h2_system_types[i]["h2_storage_type"]==ned_man.baseline_h2_storage_type]
    h2_design_key = h2_design_key[0]
    if ned_man.h2_system_types[h2_design_key]["distance_to_storage_key"] is None:
        distance = 0
    else:
        distance = ned_site.__getattribute__(ned_man.h2_system_types[h2_design_key]["distance_to_storage_key"])
    
    config.greenheart_config["site"]["distance_to_storage_km"] = distance
    config.greenheart_config["h2_storage"]["type"] = ned_man.h2_system_types[h2_design_key]["h2_storage_type"]
        
    plant_design_id = ned_man.h2_system_types[h2_design_key]["plant_design_num"]
    config.plant_design_scenario = plant_design_id
    config.design_scenario = config.greenheart_config["plant_design"]["scenario{}".format(plant_design_id)]

    return config
def update_config_for_site(
    ned_site:Site,
    config:GreenHeartSimulationConfig
    ):
    config.greenheart_config["site"]["feedstock_region"] = ned_site.feedstock_region
    config.hopp_config["site"]["data"]["lat"] = ned_site.latitude
    config.hopp_config["site"]["data"]["lon"] = ned_site.longitude

    return config
def check_config_values(
    config:GreenHeartSimulationConfig,
    ned_man: NedManager):
    config.greenheart_config["project_parameters"]["atb_year"] = ned_man.atb_year
    config.hopp_config["site"]["data"]["year"] = ned_man.resource_year
    config.hopp_config["site"]["renewable_resource_origin"] = ned_man.renewable_resource_origin
    config.hopp_config["technologies"]["wind"]["rotor_diameter"] = ned_man.rotor_diameter
    config.hopp_config["technologies"]["wind"]["turbine_rating_kw"] = ned_man.turbine_size_mw*1e3 
    config.hopp_config["technologies"]["pv"]["dc_ac_ratio"] = ned_man.dc_ac_ratio
    config.hopp_config["site"]["hub_height"] = ned_man.hub_height
    config.greenheart_config["finance_parameters"]["profast_config"] = ned_man.profast_config
    config.greenheart_config["electrolyzer"]["rating"] = ned_man.electrolyzer_size_mw
    return config

def run_baseline_site(site_info,config_input_dict,ned_output_config_dict,ned_man_dict):
    ned_site = Site.from_dict(site_info)
    ned_output_config_dict.update({"site":ned_site})
    ned_output_config_dict.update({"extra_desc":"onsite_storage"})
    ned_out = NedOutputs.from_dict(ned_output_config_dict)
    ned_man = NedManager(**ned_man_dict)


    config = GreenHeartSimulationConfig(**config_input_dict)

    ned_man.set_renewable_specs(config)
    config = check_config_values(config,ned_man)
    ned_man.set_default_hopp_technologies(config.hopp_config["technologies"])
    config = update_config_for_site(
        ned_site=ned_site,
        config=config,
        )

    config = update_config_for_baseline_cases(
        ned_site=ned_site,
        config=config,
        ned_man = ned_man,
        )
    # sweep everything with none and pipe h2 storage
    ned_res = sweep_plant_design_types(
        ned_site=ned_site,
        config = copy.deepcopy(config),
        ned_man=ned_man,
        ned_out=ned_out)
    # ned_res.write_outputs(output_dir = ned_man.output_directory,save_separately=False)
    ned_res.write_outputs(output_dir = ned_man.output_directory,save_separately=True)
    ned_man.baseline_h2_storage_type = "lined_rock_cavern"
    
    #reset outputs for geologic storage
    ned_output_config_dict.update({"extra_desc":"geologic_storage"})
    ned_out = NedOutputs.from_dict(ned_output_config_dict)
    config = update_config_for_baseline_cases(
        ned_site=ned_site,
        config=config,
        ned_man = ned_man,
        )

    ned_res = sweep_plant_design_types(
        ned_site=ned_site,
        config = copy.deepcopy(config),
        ned_man=ned_man,
        ned_out=ned_out)
    
    ned_res.write_outputs(output_dir = ned_man.output_directory,save_separately=True)
    

def setup_runs(input_config):
    input_filepath = INPUT_DIR/"v1-baseline-offgrid/equal-sized/main.yaml"
    input_config = load_yaml(input_filepath)

    sitelist_filename = SITELIST_DIR/input_config["sitelist"]
    site_list = pd.read_csv(sitelist_filename,index_col="Unnamed: 0")
    site_list = site_list.rename(columns = {
        "Balancing Area":"balancing_area",
        "Feedstock Region":"feedstock_region",
        "Distance to Rock Cavern [km]":"distance_to_rock_cavern",
        "Distance to Salt Cavern [km]":"distance_to_salt_cavern",
        "Rock Cavern Lat/Lon":"rock_cavern_loc",
        "Salt Cavern Lat/Lon":"salt_cavern_loc"})
    key_order = list(Site.get_model_defaults().keys())
    site_list = site_list[key_order]

    atb_year = input_config["atb_year"]
    resource_year = input_config["resource_year"]
    re_plant_capacity_multiplier = input_config["re_plant_capacity_multiplier"]

    filename_greenheart_config = os.path.join(str(LIB_DIR),input_config["filename_greenheart_config"])
    filename_hopp_config = os.path.join(str(LIB_DIR),input_config["filename_hopp_config"])
    filename_floris_config = os.path.join(str(LIB_DIR),input_config["filename_floris_config"])
    filename_turbine_config = os.path.join(str(LIB_DIR),input_config["filename_turbine_config"])

    electrolyzer_size_mw = input_config["electrolyzer_size_mw"]
    
    if input_config["hpc_or_local"].lower() == "hpc":
        output_dir = str(ROOT_DIR/input_config["output_dir"]/input_config["sweep_name"]/input_config["subsweep_name"])
    else:
        output_dir = str(input_config["output_dir"]/input_config["sweep_name"]/input_config["subsweep_name"])

    check_create_folder(output_dir)

    h2_storage_transport_info = input_config["h2_storage_transport_info"]
    plant_design_num_baseline = [h2_storage_transport_info[k]["plant_design_num"] for k in list(h2_storage_transport_info.keys()) \
        if h2_storage_transport_info[k]["h2_storage_type"] == input_config["baseline_options"]["baseline_h2_storage_type"]]

    config_input_dict = {
        "filename_hopp_config":filename_hopp_config,
        "filename_greenheart_config":filename_greenheart_config,
        "filename_turbine_config":filename_turbine_config,
        "filename_floris_config":filename_floris_config,
        "output_dir" :output_dir,
        "incentive_option":input_config["baseline_options"]["baseline_incentive_option"],
        "plant_design_scenario":int(plant_design_num_baseline[0]),
        }
    config_input_dict.update(input_config["greenheart_config_defaults"])
    # config = GreenHeartSimulationConfig(
    #     filename_hopp_config,
    #     filename_greenheart_config,
    #     filename_turbine_config,
    #     filename_floris_config,
    #     verbose=False,
    #     show_plots=False,
    #     save_plots=False,
    #     use_profast=True,
    #     post_processing=False,
    #     output_dir = output_dir,
    #     incentive_option=input_config["baseline_options"]["baseline_incentive_option"],
    #     plant_design_scenario=int(plant_design_num_baseline[0]),
    #     output_level=7,
    #     # grid_connection = False,
    #     # output_level=7,
    # )
    
    atb_cost_cases_filename = os.path.join(str(LIB_DIR),input_config["root_filename_atb_cost_cases"] + str(atb_year) + ".yaml")
    atb_cost_cases_hopp_cost_info_filename = os.path.join(str(LIB_DIR),input_config["root_filename_atb_cost_cases_hopp"] + str(atb_year) + ".yaml")
    profast_config_filename = os.path.join(str(LIB_DIR),input_config["root_filename_profast_config"] + str(atb_year) + ".yaml")
    atb_cost_cases_hopp = load_yaml(atb_cost_cases_hopp_cost_info_filename)
    atb_cost_cases = load_yaml(atb_cost_cases_filename)
    profast_config = load_yaml(profast_config_filename)
   
    cost_cases = atb_cost_cases["cost_cases"].keys()
    atb_costs_electrolyzer = {}
    
    for case in cost_cases:
        elec_cost = atb_cost_cases["cost_cases"][case]["electrolyzer"]
        elec_cost["electrolyzer_capex"] = elec_cost.pop("overnight_capex")
        elec_cost["replacement_cost_percent"] = elec_cost.pop("refurb_cost")
        elec_cost["cost_model"] = "custom"
        atb_costs_electrolyzer.update({case:elec_cost})
    
    if input_config["renewable_resource_origin"] == "API":
        from hopp import ROOT_DIR as hopp_root
        env_path = str(hopp_root.parent / ".env")
        from hopp.utilities.keys import set_nrel_key_dot_env
        set_nrel_key_dot_env(path = env_path)
        solar_resource_dir = str(ROOT_DIR/"resource_files"/"solar")
        wind_resource_dir = str(ROOT_DIR/"resource_files"/"wind")
        path_resource = str(ROOT_DIR/"resource_files")
        check_create_folder(solar_resource_dir)
        check_create_folder(wind_resource_dir)
        hp_cnfg = load_yaml(filename_hopp_config)
        hp_cnfg["site"].update({"path_resource":path_resource})
        new_hopp_filename = filename_hopp_config.replace(".yaml","_for_api.yaml")
        write_yaml(new_hopp_filename,hp_cnfg)
        config_input_dict.update({"filename_hopp_config":new_hopp_filename})

    
    elif input_config["renewable_resource_origin"] =="HPC":
        wtk_source_path = input_config["hpc_resource_info"]["wtk_source_path"]
        nsrdb_source_path = input_config["hpc_resource_info"]["nsrdb_source_path"]
        hp_cnfg = load_yaml(filename_hopp_config)
        hp_cnfg["site"].update({"wtk_source_path":wtk_source_path,"nsrdb_source_path":nsrdb_source_path})
        new_hopp_filename = filename_hopp_config.replace(".yaml","_for_hpc.yaml")
        write_yaml(new_hopp_filename,hp_cnfg)
        config_input_dict.update({"filename_hopp_config":new_hopp_filename})
        

    re_plant_types_multipliers = input_config["re_plant_types"]
    # h2_storage_types = [h2_storage_transport_info[k]["h2_storage_type"] for k in list(h2_storage_transport_info.keys())]
    # gh_cnfg = load_yaml(filename_greenheart_config)
    ned_output_config_dict = {
        "sweep_name":input_config["sweep_name"],
        "atb_year":atb_year,
        "subsweep_name":input_config["subsweep_name"],
        # "n_incentive_options":len(gh_cnfg["policy_parameters"].keys()),
        # "n_plant_design_types":len(re_plant_types_multipliers.keys()),
        # "n_atb_scenarios":len(cost_cases),
        # "n_storage_types":len(h2_storage_types)
        }
    # h2_storage_transport_info = input_config["h2_storage_transport_info"]
    
    # plant_design_num_baseline = [h2_storage_transport_info[k]["plant_design_num"] for k in list(h2_storage_transport_info.keys()) \
    #     if h2_storage_transport_info[k]["h2_storage_type"] == input_config["baseline_options"]["baseline_h2_storage_type"]]
   
    ned_manager = NedManager(
        output_directory=output_dir,
        renewable_resource_origin = input_config["renewable_resource_origin"],
        atb_year=atb_year,
        atb_cost_cases_hopp=atb_cost_cases_hopp,
        atb_cost_cases_electrolyzer=atb_costs_electrolyzer,
        atb_cases_desc = input_config["cost_cases"],
        h2_system_types=h2_storage_transport_info,
        profast_config=profast_config,
        baseline_atb_case=input_config["baseline_options"]["baseline_atb_case"],
        baseline_incentive_opt=input_config["baseline_options"]["baseline_incentive_option"],
        baseline_h2_storage_type=input_config["baseline_options"]["baseline_h2_storage_type"],
        re_plant_types=re_plant_types_multipliers,
        re_plant_capacity_multiplier=re_plant_capacity_multiplier,
        optimize_design=input_config["optimize_design"],
        electrolyzer_size_mw=electrolyzer_size_mw,
        resource_year=resource_year)

    config = GreenHeartSimulationConfig(**config_input_dict)
    ned_manager.set_renewable_specs(config)
    ned_manager.set_default_hopp_technologies(config.hopp_config["technologies"])

    input_data = [config_input_dict,ned_output_config_dict,ned_manager.as_dict()]
    return site_list, input_data

if __name__ == "__main__":
    start = time.perf_counter()
    site_id = 3
    input_filepath = INPUT_DIR/"v1-baseline-offgrid/equal-sized/main.yaml"
    input_config = load_yaml(input_filepath)
    site_list, inputs = setup_runs(input_config)
    config_input_dict,ned_output_config_dict,ned_man = inputs
    run_baseline_site(site_list.iloc[site_id].to_dict(),config_input_dict,ned_output_config_dict,ned_man)
    print("done")
    end = time.perf_counter()
    time_to_run = (end-start)/60
    print("Took {} min to run".format(round(time_to_run,2)))
    # run_baseline_site(site_list.iloc[0].to_dict(),config_input_dict,ned_output_config_dict,ned_manager.as_dict())
    # ned_manager.set_renewable_specs(config)
    # config = check_config_values(config,ned_manager)

    # ned_manager.set_default_hopp_technologies(config.hopp_config["technologies"])

    
    # this_site = site_list.iloc[0][key_order].to_dict()
    # ned_site = Site.from_dict(this_site)
    
    
    


    # config = update_config_for_site(
    #     ned_site=ned_site,
    #     config=config,
    #     )
    # config = update_config_for_baseline_cases(
    #     ned_site=ned_site,
    #     config=config,
    #     ned_man = ned_manager,
    #     )

    

    # ned_out = NedOutputs.from_dict({"site":ned_site,
    # "sweep_name":input_config["sweep_name"],
    # "atb_year":atb_year,
    # "subsweep_name":input_config["subsweep_name"],
    # "n_incentive_options":len(config.greenheart_config["policy_parameters"].keys()),
    # "n_plant_design_types":len(re_plant_types_multipliers.keys()),
    # "n_atb_scenarios":len(cost_cases),
    # "n_storage_types":len(h2_storage_types)})
    
    

    # ned_res = sweep_plant_design_types(
    #     ned_site=ned_site,
    #     config = copy.deepcopy(config),
    #     ned_man=ned_manager,
    #     ned_out=ned_out)
    # ned_res.write_outputs(output_dir = ned_manager.output_directory,save_separately=False)
  
    # print("done")

    # # copy.deepcopy(config)
    # []

