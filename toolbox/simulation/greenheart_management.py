import greenheart.tools.eco.electrolysis as he_elec
import greenheart.tools.eco.finance as he_fin
import greenheart.tools.eco.hopp_mgmt as he_hopp
import greenheart.tools.eco.utilities as he_util
import greenheart.tools.eco.hydrogen_mgmt as he_h2

from greenheart.simulation.greenheart_simulation import (
    run_simulation,
    GreenHeartSimulationConfig,
    setup_greenheart_simulation,
)
# from greenheart.tools.optimization.gc_run_greenheart import run_greenheart,setup_greenheart_simulation
from toolbox.tools.wind_layout_tools import make_site_boundaries_for_square_layout
import numpy as np
from hopp.tools.analysis import create_cost_calculator
import copy
from toolbox.simulation.results import LCOHResults,LCOEResults,FinanceResults, PhysicsResults
def set_up_greenheart_run_renewables(config:GreenHeartSimulationConfig,power_for_peripherals_kw = 0.0):
    
    config, hi, wind_cost_results = setup_greenheart_simulation(config=config,power_for_peripherals_kw=power_for_peripherals_kw)

    hopp_results = he_hopp.run_hopp(
        hi,
        project_lifetime=config.greenheart_config["project_parameters"][
            "project_lifetime"
        ],
        verbose=config.verbose,
    )
    if wind_cost_results == None:
        if "wind" in config.hopp_config["technologies"].keys():
            if config.design_scenario["wind_location"] == "onshore":
                wind_config = he_fin.WindCostConfig(
                    design_scenario=config.design_scenario,
                    hopp_config=config.hopp_config,
                    greenheart_config=config.greenheart_config,
                    turbine_config=config.turbine_config,
                    hopp_interface=hopp_results["hopp_interface"],
                )

                wind_cost_results = he_fin.run_wind_cost_model(
                    wind_cost_inputs=wind_config, verbose=False,
                )
    return config,hi,wind_cost_results, hopp_results

def update_hopp_costs(hopp_results,hopp_cost_info):
    hopp_cost_info = copy.deepcopy(hopp_cost_info)
    om_cost_info = {}
    keys_to_remove = []
    for key in hopp_cost_info:
        if "_om_per_kw" in key:
            om_cost_info.update({key: hopp_cost_info[key]})
            keys_to_remove.append(key)
        if "_om_per_mwh" in key:
                om_cost_info.update({key: hopp_cost_info[key]})
                keys_to_remove.append(key)
    for key in keys_to_remove: hopp_cost_info.pop(key)
    hopp_results["hybrid_plant"].cost_model = create_cost_calculator(hopp_results["hybrid_plant"], **hopp_cost_info or {})
    hopp_results["hybrid_plant"].set_om_costs(**om_cost_info)
    hopp_results["hybrid_plant"].calculate_installed_cost()
    hopp_results["hybrid_plant"].calculate_financials()
    hopp_results["hybrid_plant"].simulate_financials(30)

    return hopp_results

def update_electrolysis_costs(greenheart_config,electrolyzer_physics_results,electrolyzer_costs):
    greenheart_config["electrolyzer"].update(electrolyzer_costs)
    electrolyzer_cost_results = he_elec.run_electrolyzer_cost(electrolyzer_physics_results,hopp_config=None,greenheart_config=greenheart_config,design_scenario=None,verbose = False)
    return electrolyzer_cost_results
def estimate_power_for_peripherals_kw_land_based(greenheart_config,hybrid_plant_capacity_kWac,design_scenario):
    # he_elec.size_electrolyzer_for_hydrogen_demand
    pem_1MW = he_elec.create_1MW_reference_PEM()
    electrolyzer_size_kw = greenheart_config["electrolyzer"]["rating"]*1e3
    if electrolyzer_size_kw>hybrid_plant_capacity_kWac:
        #electrolyzer not likely on at full power
        n = hybrid_plant_capacity_kWac/pem_1MW.output_dict["BOL Efficiency Curve Info"]["Power Consumed [kWh]"].max()
    else:
        #electrolyzer likely on at full power
        n = electrolyzer_size_kw/pem_1MW.output_dict["BOL Efficiency Curve Info"]["Power Consumed [kWh]"].max()
    
    max_h2_prod_kg_pr_hr = n*pem_1MW.output_dict["BOL Efficiency Curve Info"]["H2 Produced"].max()
    
    fake_res = {"H2_Results":{"Hydrogen Hourly Production [kg/hr]":[max_h2_prod_kg_pr_hr]*8760}}
    (
        h2_transport_compressor,
        h2_transport_compressor_results,
    ) = he_h2.run_h2_transport_compressor(
        greenheart_config,
        fake_res,
        design_scenario,
        verbose=False,
    )
    h2_transport_compressor_power_kw = h2_transport_compressor_results["compressor_power"]  # kW
    return h2_transport_compressor_power_kw

def run_physics_and_design(
    hopp_results,
    wind_cost_results,
    design_scenario,
    orbit_config,
    hopp_config,
    greenheart_config,
    turbine_config,
    power_for_peripherals_kw_in = 0.0,
    ):

    hopp_results_internal = dict(hopp_results)

    # set energy input profile
    ### subtract peripheral power from supply to get what is left for electrolyzer
    remaining_power_profile_in = np.zeros_like(
        hopp_results["combined_hybrid_power_production_hopp"]
    )

    high_count = sum(
        np.asarray(hopp_results["combined_hybrid_power_production_hopp"])
        >= power_for_peripherals_kw_in
    )
    total_peripheral_energy = power_for_peripherals_kw_in * 365 * 24
    distributed_peripheral_power = total_peripheral_energy / high_count
    for i in range(len(hopp_results["combined_hybrid_power_production_hopp"])):
        r = (
            hopp_results["combined_hybrid_power_production_hopp"][i]
            - distributed_peripheral_power
        )
        if r > 0:
            remaining_power_profile_in[i] = r

    hopp_results_internal["combined_hybrid_power_production_hopp"] = tuple(
        remaining_power_profile_in
    )

    # run electrolyzer physics model
    electrolyzer_physics_results = he_elec.run_electrolyzer_physics(
        greenheart_config,
        input_power_profile_kW = hopp_results_internal["combined_hybrid_power_production_hopp"],
        verbose=False,
    )
    if electrolyzer_physics_results["H2_Results"]["Hydrogen Hourly Production [kg/hr]"].sum() == 0:
        print("---- ISSUE ----")
        print("max power production: {}".format(max(hopp_results_internal["combined_hybrid_power_production_hopp"])))
        []
    desal_results = he_elec.run_desal(
            hopp_config, electrolyzer_physics_results, design_scenario, verbose = False
        )
    h2_pipe_array_results = he_h2.run_h2_pipe_array(
            greenheart_config,
            hopp_config,
            turbine_config,
            wind_cost_results,
            electrolyzer_physics_results,
            design_scenario,
            verbose = False,
        )
    # compressor #TODO size correctly
    (
        h2_transport_compressor,
        h2_transport_compressor_results,
    ) = he_h2.run_h2_transport_compressor(
        greenheart_config,
        electrolyzer_physics_results,
        design_scenario,
        verbose=False,
    )

    if design_scenario["wind_location"] == "offshore":
        h2_transport_pipe_results = he_h2.run_h2_transport_pipe(
            orbit_config,
            greenheart_config,
            electrolyzer_physics_results,
            design_scenario,
            verbose=False,
        )

    elif (design_scenario["wind_location"] == "onshore") and (design_scenario["transportation"] == "pipeline"):
        orb_config = {"site":{"distance_to_landfall":greenheart_config["site"]["distance_to_storage_km"]}}
        h2_transport_pipe_results = he_h2.run_h2_transport_pipe(
        orb_config,
        greenheart_config,
        electrolyzer_physics_results,
        design_scenario,
        verbose=False,
    )

    elif (design_scenario["wind_location"] == "onshore") and (design_scenario["transportation"] != "pipeline"):
        h2_transport_pipe_results = {
            "total capital cost [$]": [0 * 5433290.0184895478],
            "annual operating cost [$]": [0.0],
        }
    else:
        h2_transport_pipe_results = {
            "total capital cost [$]": [0 * 5433290.0184895478],
            "annual operating cost [$]": [0.0],
        }

    # pressure vessel storage
    pipe_storage, h2_storage_results = he_h2.run_h2_storage(
        hopp_config,
        greenheart_config,
        turbine_config,
        electrolyzer_physics_results,
        design_scenario,
        verbose=False,
    )

    platform_results = he_h2.run_equipment_platform(
        hopp_config,
        greenheart_config,
        orbit_config,
        design_scenario,
        hopp_results,
        electrolyzer_physics_results,
        h2_storage_results,
        desal_results,
        verbose=False,
    )

    electrolyzer_cost_results = he_elec.run_electrolyzer_cost(
            electrolyzer_physics_results,
            hopp_config,
            greenheart_config,
            design_scenario,
            verbose=False,
        )
    h2_prod_store_results = [electrolyzer_cost_results, h2_storage_results]
    h2_transport_results = [h2_pipe_array_results, h2_transport_compressor_results, h2_transport_pipe_results]
    offshore_component_results = [desal_results, platform_results, wind_cost_results]

    
    total_energy_available = np.sum(
        hopp_results["combined_hybrid_power_production_hopp"]
    )

    ### get all energy non-electrolyzer usage in kw
    desal_power_kw = desal_results["power_for_desal_kw"]

    h2_transport_compressor_power_kw = h2_transport_compressor_results["compressor_power"]  # kW

    h2_storage_energy_kwh = h2_storage_results["storage_energy"]
    h2_storage_power_kw = h2_storage_energy_kwh * (1.0 / (365 * 24))

    # if transport is not HVDC and h2 storage is on shore, then power the storage from the grid
    if (design_scenario["transportation"] == "pipeline") and (
        design_scenario["h2_storage_location"] == "onshore"
    ):
        total_accessory_power_renewable_kw = (
            desal_power_kw + h2_transport_compressor_power_kw
        )
        total_accessory_power_grid_kw = h2_storage_power_kw
    else:
        total_accessory_power_renewable_kw = (
            desal_power_kw + h2_transport_compressor_power_kw + h2_storage_power_kw
        )
        total_accessory_power_grid_kw = 0.0

    ### subtract peripheral power from supply to get what is left for electrolyzer and also get grid power
    remaining_power_profile = np.zeros_like(
        hopp_results["combined_hybrid_power_production_hopp"]
    )
    grid_power_profile = np.zeros_like(
        hopp_results["combined_hybrid_power_production_hopp"]
    )
    for i in range(len(hopp_results["combined_hybrid_power_production_hopp"])):
        r = (
            hopp_results["combined_hybrid_power_production_hopp"][i]
            - total_accessory_power_renewable_kw
        )
        grid_power_profile[i] = total_accessory_power_grid_kw
        if r > 0:
            remaining_power_profile[i] = r
    phy_res = PhysicsResults(
        hopp_results = hopp_results_internal,
        electrolyzer_physics_results=electrolyzer_physics_results,
        h2_storage_results=h2_storage_results,
        h2_transport_pipe_results=h2_transport_pipe_results,
        h2_transport_compressor_results=h2_transport_compressor_results)
    phy_res.update_h2_design_scenario(greenheart_config["h2_storage"]["type"],design_scenario["transportation"])
    return (
        phy_res,
        electrolyzer_physics_results,
        hopp_results,
        h2_prod_store_results,
        h2_transport_results,
        offshore_component_results,
        total_accessory_power_renewable_kw
    )
    
    
def calc_capex_and_opex(hopp_results, h2_prod_store_results, h2_transport_results, offshore_component_results, config:GreenHeartSimulationConfig):
    electrolyzer_cost_results, h2_storage_results = h2_prod_store_results
    h2_pipe_array_results, h2_transport_compressor_results, h2_transport_pipe_results = h2_transport_results
    
    desal_results, platform_results, wind_cost_results = offshore_component_results
    wind_cost_results = None
    capex, capex_breakdown = he_fin.run_capex(
        hopp_results,
        wind_cost_results,
        electrolyzer_cost_results,
        h2_pipe_array_results,
        h2_transport_compressor_results,
        h2_transport_pipe_results,
        h2_storage_results,
        config.hopp_config,
        config.greenheart_config,
        config.design_scenario,
        desal_results,
        platform_results,
        verbose=False,
    )
    opex_annual, opex_breakdown_annual = he_fin.run_opex(
        hopp_results,
        wind_cost_results,
        electrolyzer_cost_results,
        h2_pipe_array_results,
        h2_transport_compressor_results,
        h2_transport_pipe_results,
        h2_storage_results,
        config.hopp_config,
        config.greenheart_config,
        desal_results,
        platform_results,
        verbose=config.verbose,
        total_export_system_cost=capex_breakdown["electrical_export_system"],
    )
    fin_res = FinanceResults(
        capex_breakdown = capex_breakdown,
        opex_breakdown_annual = opex_breakdown_annual,
        atb_year = config.greenheart_config["project_parameters"]["atb_year"],
        atb_scenario = "",
        policy_scenario = config.incentive_option,
        re_plant_type = "",
        h2_storage_type = config.greenheart_config["h2_storage"]["type"],
        h2_transport_type = config.design_scenario["transportation"]

    )
    return capex_breakdown, opex_breakdown_annual, fin_res

def calc_lcoe(
    hopp_results,
    capex_breakdown,
    opex_breakdown_annual,
    wind_cost_results,
    config:GreenHeartSimulationConfig
    ):
    lcoe, pf_lcoe = he_fin.run_profast_lcoe(
            config.greenheart_config,
            wind_cost_results,
            capex_breakdown,
            opex_breakdown_annual,
            hopp_results,
            config.incentive_option,
            config.design_scenario,
            verbose=False,
            show_plots=False,
            save_plots=False,
            output_dir=config.output_dir,
        )

    lcoe_res = LCOEResults(
        lcoe_pf = pf_lcoe,
        lcoe = lcoe,
        atb_year = config.greenheart_config["project_parameters"]["atb_year"],
        policy_scenario = config.incentive_option,
        atb_scenario = "",
        re_plant_type = "",
        )
    return lcoe, pf_lcoe, lcoe_res

def calc_offgrid_lcoh(
    hopp_results,
    capex_breakdown,
    opex_breakdown_annual,
    wind_cost_results,
    electrolyzer_physics_results,
    total_accessory_power_renewable_kw,
    total_accessory_power_grid_kw,
    config:GreenHeartSimulationConfig
    ):

    lcoh, pf_lcoh = he_fin.run_profast_full_plant_model(
            config.greenheart_config,
            wind_cost_results,
            electrolyzer_physics_results,
            capex_breakdown,
            opex_breakdown_annual,
            hopp_results,
            config.incentive_option,
            config.design_scenario,
            total_accessory_power_renewable_kw,
            total_accessory_power_grid_kw,
            verbose=False,
            show_plots=False,
            save_plots=False,
            output_dir=config.output_dir,
        )
    
    lcoh_res = LCOHResults(
                lcoh_pf = pf_lcoh,
                lcoh = lcoh,
                atb_year = config.greenheart_config["project_parameters"]["atb_year"],
                atb_scenario="",
                policy_scenario=config.incentive_option,
                re_plant_type="",
                h2_storage_type=config.greenheart_config["h2_storage"]["type"],
                h2_transport_design = config.design_scenario["transportation"])
    return lcoh, pf_lcoh, lcoh_res

def calc_grid_connected_lcoh(config:GreenHeartSimulationConfig):
    pass