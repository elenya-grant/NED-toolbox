
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
from toolbox.simulation.results import NedOutputs
from toolbox.simulation.run_offgrid_onshore import check_config_values, update_config_for_site, update_config_for_baseline_cases
from toolbox.simulation.run_offgrid_onshore import run_lcoh_lcoe,sweep_atb_cost_cases
# from greenheart.tools.optimization.gc_run_greenheart import run_greenheart
from greenheart.simulation.greenheart_simulation import setup_greenheart_simulation, run_simulation
from hopp.simulation.technologies.sites import SiteInfo
from toolbox.simulation.results import ConfigTracker

def initialize_run(site_info,config_input_dict,ned_output_config_dict,ned_man_dict):
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
        ned_site = ned_site,
        config = config,
        ned_man = ned_man,
        )
    return ned_site, ned_man, ned_out, config

def update_renewable_plant_design(ned_man,hopp_config,wind_capacity_mw,pv_capacity_mwac,include_battery: bool,hopp_site_main:SiteInfo):
    hopp_config = int_tool.update_hopp_config_for_wind_capacity(wind_capacity_mw,ned_man,hopp_config)
    hopp_config = int_tool.update_hopp_config_for_solar_capacity(pv_capacity_mwac,ned_man,hopp_config)
    hopp_config = int_tool.update_hopp_config_for_battery(include_battery,ned_man,hopp_config)
    hopp_config = int_tool.update_hopp_site_for_case(pv_capacity_mwac,wind_capacity_mw,hopp_site_main.wind_resource,hopp_site_main.solar_resource,hopp_config)
    return hopp_config

# def mix_generation_profiles():
#     gh_mgmt.update_hopp_costs(hopp_results,hopp_cost_info)
#     hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[atb_cost_case])

def run_simple_single_simulation(
    ned_man: NedManager,
    ned_out: NedOutputs,
    config:GreenHeartSimulationConfig,
    hopp_site_main:SiteInfo,
    wind_capacity_mw,
    pv_capacity_mwac,
    include_battery,
    ancillary_power_usage_kw = 0.0,
    total_accessory_power_grid_kw = 0,
    save_detailed_results = False,
    output_level = 1,
    hopp_results = None,
    run_lcoh = True,
    ):
    plant_desc = ""
    if wind_capacity_mw>0:
        plant_desc += "wind"
    if pv_capacity_mwac>0:
        if plant_desc == "":
            plant_desc = "pv"
        else:
            plant_desc += "-pv"
    if include_battery:
        plant_desc +="-battery"
        
    #1) set wind, solar, and battery capaities & update hopp_config
    hopp_config = copy.deepcopy(config.hopp_config)
    hopp_config = update_renewable_plant_design(ned_man,hopp_config,wind_capacity_mw,pv_capacity_mwac,include_battery,hopp_site_main)
    if include_battery:
        minimum_load_MW = ned_man.electrolyzer_size_mw*config.greenheart_config["electrolyzer"]["turndown_ratio"]
        hopp_config["site"]["desired_schedule"] = [minimum_load_MW]*8760
        hopp_config["site"]["curtailment_value_type"] = "grid"
        hopp_config["technologies"]["grid"]["interconnect_kw"] = ned_man.electrolyzer_size_mw*1e3
    config.hopp_config = hopp_config
    #2) simulate renewable using HOPP
    if hopp_results is None:
        config,hi,wind_cost_results, hopp_results = gh_mgmt.set_up_greenheart_run_renewables(config,power_for_peripherals_kw=ancillary_power_usage_kw)
    else:
        wind_cost_results = None
    #3) simulate hydrogen system physics
    if ned_man.ancillary_power_solver_method == "simple_solver":
        ghg_res = gh_mgmt.solve_for_ancillary_power_and_run(
            hopp_results = hopp_results,
            wind_cost_results = wind_cost_results,
            design_scenario = config.design_scenario,
            orbit_config = config.orbit_config,
            hopp_config = config.hopp_config,
            greenheart_config = config.greenheart_config,
            turbine_config = config.turbine_config,
            power_for_peripherals_kw_inital_guess=0.0
            )
    phys_res, electrolyzer_physics_results, hopp_results,h2_prod_store_results, h2_transport_results,offshore_component_results,total_accessory_power_renewable_kw = ghg_res
    #5) calculate costs
    #5a) update hopp and electrolyzer costs
    hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[ned_man.baseline_atb_case])
    electrolyzer_cost_results = gh_mgmt.update_electrolysis_costs(config.greenheart_config,electrolyzer_physics_results,ned_man.atb_cost_cases_electrolyzer[ned_man.baseline_atb_case])
    h2_prod_store_results[0] = electrolyzer_cost_results
    #5b) calc capex and opex breakdown
    capex_breakdown, opex_breakdown_annual, fin_res = gh_mgmt.calc_capex_and_opex(
            hopp_results, 
            h2_prod_store_results, 
            h2_transport_results, 
            offshore_component_results, 
            config
            )
    if run_lcoh:
        #6) simulate financials - calculate LCOE/LCOH
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
    # print("H2 storage capacity: {}".format(h2_prod_store_results[1]["h2_storage_capacity_kg"]))
    if save_detailed_results:
        ned_out.add_Physics_Results(phys_res)
        if run_lcoh:
            ned_out.add_LCOH_Results(lcoh_res)
        ned_out.add_Finance_Results(fin_res)
        phys_res.update_re_plant_type(re_plant_type=plant_desc)
        phys_res.add_ancillary_power_results("Estimated Ancillary Power Usage [kW]",ancillary_power_usage_kw)
        phys_res.add_ancillary_power_results("Actual Ancillary Power Usage [kW]",total_accessory_power_renewable_kw)
        # gh_cfg = ConfigTracker(
        #     config=config,
        #     atb_scenario = atb_cost_case,
        #     re_plant_type = re_plant_desc)
        # ned_out.add_GreenHEART_Config(gh_config)
    if output_level == 1:
        return lcoh
    elif output_level == 2:
        return lcoh, hopp_results, electrolyzer_physics_results
    elif output_level == 3:
        return ned_out
    elif output_level == 4:
        return lcoh,ned_out
    elif output_level == 5:
        if "wind" in hopp_config["technologies"]:
            wind_size_mw = hopp_config["technologies"]["wind"]["num_turbines"]*ned_man.turbine_size_mw
        else:
            wind_size_mw = 0.0
        if "pv" in hopp_config["technologies"]:
            pv_size_mwdc = hopp_config["technologies"]["pv"]["system_capacity_kw"]/1e3
        else:
            pv_size_mwdc = 0.0
        return lcoh,wind_size_mw,pv_size_mwdc, h2_prod_store_results[1]["h2_storage_capacity_kg"],electrolyzer_physics_results["H2_Results"]["Life: Capacity Factor"]
    elif output_level == 6:
        return ned_out,ghg_res,wind_cost_results,hopp_config
    elif output_level==7:
        return lcoh, hopp_results, capex_breakdown, opex_breakdown_annual, wind_cost_results, electrolyzer_physics_results, config
    elif output_level==8:
        return lcoh, hopp_results, capex_breakdown, opex_breakdown_annual, wind_cost_results, electrolyzer_physics_results, config, h2_prod_store_results[1]["h2_storage_capacity_kg"]
    elif output_level == 9:
        if run_lcoh:
            return lcoh, capex_breakdown, opex_breakdown_annual, wind_cost_results, electrolyzer_physics_results, h2_prod_store_results, h2_transport_results, offshore_component_results
        else:
            return capex_breakdown, opex_breakdown_annual, wind_cost_results, electrolyzer_physics_results, h2_prod_store_results, h2_transport_results, offshore_component_results

            
             
# def run_plant_calc_lcoh(self,config):
#     ancillary_power_usage_kw = gh_mgmt.estimate_power_for_peripherals_kw_land_based(config.greenheart_config,renewable_plant_capacity_MWac*1e3,config.design_scenario)
#     ancillary_power_for_grid_sizing_and_battery = ancillary_power_usage_kw + adjustment_ancillary_power_usage_kw
#     config,hi,wind_cost_results, hopp_results = gh_mgmt.set_up_greenheart_run_renewables(config,power_for_peripherals_kw=ancillary_power_for_grid_sizing_and_battery)
#     ghg_res = gh_mgmt.run_physics_and_design(
#             hopp_results = hopp_results,
#             wind_cost_results = wind_cost_results,
#             design_scenario = config.design_scenario,
#             orbit_config = config.orbit_config,
#             hopp_config = config.hopp_config,
#             greenheart_config = config.greenheart_config,
#             turbine_config = config.turbine_config,
#             power_for_peripherals_kw_in=ancillary_power_usage_kw)
#     phys_res, electrolyzer_physics_results, hopp_results,h2_prod_store_results, h2_transport_results,offshore_component_results,total_accessory_power_renewable_kw = ghg_res
    
#     phys_res.update_re_plant_type(re_plant_type=plant_desc)
#     ned_out.add_Physics_Results(phys_res)
#     hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[atb_cost_case])
#     lcoh = run_simulation(config)
#     pass


