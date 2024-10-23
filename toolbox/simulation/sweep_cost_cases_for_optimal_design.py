import toolbox.simulation.run_offgrid_onshore as run_func
from hopp.simulation.technologies.sites import SiteInfo
from toolbox.utilities.ned_logger import site_logger as slog
from toolbox.simulation.results import NedOutputs #, FinanceResults,PhysicsResults
from toolbox.simulation.results import ConfigTracker
from greenheart.simulation.greenheart_simulation import GreenHeartSimulationConfig
from toolbox.simulation.plant.design.base_optimization import OptimalDesign
from typing import List
import copy
from toolbox.simulation.ned_site import Site, NedManager
from toolbox.simulation.run_single_case import run_simple_single_simulation
import toolbox.simulation.greenheart_management as gh_mgmt
def make_objects_for_two_storage_scenarios(site_info,config_input_dict,ned_output_config_dict,ned_man_dict):
    ned_site = Site.from_dict(site_info)
    ned_output_config_dict.update({"site":ned_site})
    ned_output_config_dict.update({"extra_desc":"onsite_storage"})
    ned_out_onsite = NedOutputs.from_dict(ned_output_config_dict)
    ned_man_onsite = NedManager(**ned_man_dict)
    config_onsite = GreenHeartSimulationConfig(**config_input_dict)

    ned_man_onsite.set_renewable_specs(config_onsite)
    config_onsite = run_func.check_config_values(config_onsite,ned_man_onsite)
    ned_man_onsite.set_default_hopp_technologies(config_onsite.hopp_config["technologies"])
    config_onsite = run_func.update_config_for_site(
        ned_site=ned_site,
        config=config_onsite,
        )

    config_onsite = run_func.update_config_for_baseline_cases(
        ned_site=ned_site,
        config=config_onsite,
        ned_man = ned_man_onsite,
        )

    # make geologic storage types
    ned_output_config_dict.update({"extra_desc":"geologic_storage"})
    ned_out_geo = NedOutputs.from_dict(ned_output_config_dict)
    ned_man_geo = NedManager(**ned_man_dict)
    ned_man_geo.baseline_h2_storage_type = "lined_rock_cavern"
    config_geo = GreenHeartSimulationConfig(**config_input_dict)
    ned_man_geo.set_renewable_specs(config_geo)
    config_geo = run_func.check_config_values(config_geo,ned_man_geo)
    ned_man_geo.set_default_hopp_technologies(config_geo.hopp_config["technologies"])
    config_geo = run_func.update_config_for_site(
        ned_site=ned_site,
        config = config_geo,
        )

    config_geo = run_func.update_config_for_baseline_cases(
        ned_site=ned_site,
        config=config_geo,
        ned_man = ned_man_geo,
        )
    return ned_site,[ned_out_geo,ned_man_geo,config_geo],[ned_out_onsite,ned_man_onsite,config_onsite]

def sweep_custom_plant_designs(
    site_info,
    config_input_dict,
    ned_output_config_dict,
    ned_man_dict,
    hopp_site_main:SiteInfo,
    custom_plant_designs:List[OptimalDesign]):
    # extraneous_site_info_inputs = ['simplex_data', 'simplex_case_info', 'design_variables_info', 'merit_figure']
    # [,'merit_figures']
    extraneous_site_info_inputs = ['initial_simplex_data','initial_simplex','full_simplex','optimization_tracker','optimization_simplex','design_variables_info','merit_figures','design_variables','design_variables_mapper']
    for e in extraneous_site_info_inputs:
        if e in site_info.keys():
            site_info.pop(e)
    ned_site,geo_objs,onsite_obj = make_objects_for_two_storage_scenarios(site_info,config_input_dict,ned_output_config_dict,ned_man_dict)
    
    ned_out_onsite,ned_man_onsite,config_onsite = onsite_obj
    if ned_man_onsite.baseline_h2_storage_type == "none":
        next_h2_storage_type_onsite = "pipe"
    elif ned_man_onsite.baseline_h2_storage_type == "pipe":
        next_h2_storage_type_onsite = "none"
    
    for i in range(len(custom_plant_designs)):
        re_plant_desc = custom_plant_designs[i].optimization_design_desc
        # run onsite storage types
        ned_out_onsite,ghg_res,wind_cost_results,hopp_config_onsite = run_simple_single_simulation(
            ned_man_onsite,
            ned_out_onsite,
            config_onsite,
            hopp_site_main,
            wind_capacity_mw = custom_plant_designs[i].wind_size_mw,
            pv_capacity_mwac = custom_plant_designs[i].pv_capacity_mwac,
            include_battery = custom_plant_designs[i].include_battery,
            # ancillary_power_usage_kw,
            save_detailed_results = True,
            output_level=6)
    
        phys_res, electrolyzer_physics_results, hopp_results,h2_prod_store_results, h2_transport_results,offshore_component_results,total_accessory_power_renewable_kw = ghg_res
        config_onsite.hopp_config = hopp_config_onsite
        ned_out_onsite = run_func.sweep_atb_cost_cases(
            ned_site,
            ned_man_onsite,
            ned_out_onsite,
            re_plant_desc,
            hopp_results, 
            electrolyzer_physics_results,
            h2_prod_store_results, 
            h2_transport_results, 
            offshore_component_results, 
            config_onsite,
            total_accessory_power_renewable_kw,
            wind_cost_results,
            total_accessory_power_grid_kw = 0.0,
            sweep_incentives = True,
            new_h2_storage_type = next_h2_storage_type_onsite
            )
        

        # run geologic storage cases
        ned_out_geo,ned_man_geo,config_geo = geo_objs
        if ned_man_geo.baseline_h2_storage_type == "lined_rock_cavern":
            next_h2_storage_type_geo = "salt_cavern"
        elif ned_man_geo.baseline_h2_storage_type == "salt_cavern":
            next_h2_storage_type_geo = "lined_rock_cavern"
        ned_out_geo,ghg_res,wind_cost_results,hopp_config_geo = run_simple_single_simulation(
            ned_man_geo,
            ned_out_geo,
            config_geo,
            hopp_site_main,
            wind_capacity_mw = custom_plant_designs[i].wind_size_mw,
            pv_capacity_mwac = custom_plant_designs[i].pv_capacity_mwac,
            include_battery = custom_plant_designs[i].include_battery,
            save_detailed_results = True,
            output_level=6,
            hopp_results=hopp_results)
        phys_res, electrolyzer_physics_results, hopp_results,h2_prod_store_results, h2_transport_results,offshore_component_results,total_accessory_power_renewable_kw = ghg_res
        config_geo.hopp_config = hopp_config_geo
        ned_out_geo = run_func.sweep_atb_cost_cases(
            ned_site,
            ned_man_geo,
            ned_out_geo,
            re_plant_desc,
            hopp_results, 
            electrolyzer_physics_results,
            h2_prod_store_results, 
            h2_transport_results, 
            offshore_component_results, 
            config_geo,
            total_accessory_power_renewable_kw,
            wind_cost_results,
            total_accessory_power_grid_kw = 0.0,
            sweep_incentives = True,
            new_h2_storage_type = next_h2_storage_type_geo
            )
    ned_out_geo.write_outputs(output_dir = ned_man_geo.output_directory,save_wind_solar_generation = False)
    ned_out_onsite.write_outputs(output_dir = ned_man_onsite.output_directory,save_wind_solar_generation = True)
        # ghg_res = gh_mgmt.solve_for_ancillary_power_and_run(
        #         hopp_results = hopp_results,
        #         wind_cost_results = wind_cost_results,
        #         design_scenario = config.design_scenario,
        #         orbit_config = config.orbit_config,
        #         hopp_config = config.hopp_config,
        #         greenheart_config = config.greenheart_config,
        #         turbine_config = config.turbine_config,
        #         power_for_peripherals_kw_inital_guess=0.0
        #         )


