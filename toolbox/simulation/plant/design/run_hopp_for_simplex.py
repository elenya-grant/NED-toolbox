# from toolbox.simulation.plant.design.site_simplex import SiteSimplex
import numpy as np
from toolbox.simulation.results import NedOutputs
# from toolbox.simulation.ned_site import Site
from toolbox.simulation.run_offgrid_onshore import sweep_atb_cost_cases
from toolbox.simulation.run_single_case import run_simple_single_simulation
import toolbox.simulation.plant.design.optimization_tools as opt_tools
import toolbox.simulation.greenheart_management as gh_mgmt
from hopp.simulation.hybrid_simulation import HybridSimulation
import pandas as pd
from hopp.simulation.technologies.dispatch.hybrid_dispatch_builder_solver import HybridDispatchBuilderSolver
from hopp.simulation.technologies.battery import Battery
from hopp.simulation.technologies.grid import Grid
import os
from hopp.simulation.hybrid_simulation import HybridSimulationOutput,HybridSimulation
from toolbox.utilities.ned_logger import site_logger as slog

def convert_ned_out_to_simplex(ned_out,wind_size_mw,pv_size_mwdc,include_battery,save_simplex_detailed = True):
    simplex_keys = ["wind_size_mw","pv_size_mwdc","battery"] #,"lcoh-delivered","lcoh-produced"]
    
    design_keys = ["wind_size_mw","pv_size_mwdc","battery"]
    design_vals = [wind_size_mw,pv_size_mwdc,include_battery]
    
    if save_simplex_detailed:
        lcoh_summary = ned_out.make_LCOH_detailed_results()
        d_lcoh_keys = ["lcoh-delivered","lcoh-delivered_pf_config"]
        p_lcoh_keys = ["lcoh-produced","lcoh-produced_pf_config"]
        d_lcoh_mapper = {"lcoh":"lcoh-delivered","lcoh_pf_config":"lcoh-delivered_pf_config"}
        p_lcoh_mapper = {"lcoh":"lcoh-produced","lcoh_pf_config":"lcoh-produced_pf_config"}
    else:
        lcoh_summary = ned_out.make_LCOH_summary_results()
        d_lcoh_keys = ["lcoh-delivered"]
        p_lcoh_keys = ["lcoh-produced"]
        d_lcoh_mapper = {"lcoh":"lcoh-delivered"}
        p_lcoh_mapper = {"lcoh":"lcoh-produced"}
    simplex_keys += d_lcoh_keys
    simplex_keys += p_lcoh_keys
    lcoh_keys = ["atb_scenario","atb_year","re_plant_type","h2_transport_design"]
    
    # lcoh_produced = lcoh_summary[lcoh_summary["h2_storage_type"]=="none"]
    # lcoh_produced = lcoh_produced.rename(columns={"lcoh":"lcoh-produced"})
    lcoh_produced = lcoh_summary[lcoh_summary["h2_storage_type"]=="none"]
    lcoh_produced = lcoh_produced.rename(columns=p_lcoh_mapper)
    
    # lcoh_delivered = lcoh_summary[lcoh_summary["h2_storage_type"]!="none"]
    # lcoh_delivered = lcoh_delivered.rename(columns={"lcoh":"lcoh-delivered"})
    lcoh_delivered = lcoh_summary[lcoh_summary["h2_storage_type"]!="none"]
    lcoh_delivered = lcoh_delivered.rename(columns=d_lcoh_mapper)
    
    # lcoh_simplex = pd.merge(left=lcoh_delivered[["lcoh-delivered"]+lcoh_keys],right=lcoh_produced[["lcoh-produced"]+lcoh_keys],on=["atb_scenario","atb_year","h2_transport_design","re_plant_type"])
    lcoh_simplex = pd.merge(left=lcoh_delivered[d_lcoh_keys+lcoh_keys],right=lcoh_produced[p_lcoh_keys+lcoh_keys],on=["atb_scenario","atb_year","h2_transport_design","re_plant_type"])
    
    design = pd.DataFrame([design_vals]*len(lcoh_simplex),columns=design_keys)
    lcoh_simplex = pd.concat([design,lcoh_simplex],axis=1)
    lcoh_simplex = lcoh_simplex[simplex_keys + lcoh_keys]
    
    if save_simplex_detailed:
        lcoe_summary = ned_out.make_LCOE_detailed_results()
    else:
        lcoe_summary = ned_out.make_LCOE_summary_results()
    lcoe_simplex = pd.concat([design,lcoe_summary],axis=1)

    new_ned_out = NedOutputs.from_dict(ned_out.as_dict())
    return lcoh_simplex,lcoe_simplex,new_ned_out
def update_hopp_for_generation_profiles(hybrid_plant,wind_size_mw,wind_generation_profile,desired_schedule_kw,interconnect_kw):
    
    
    battery_config = hybrid_plant.tech_config.battery
    grid_config = hybrid_plant.tech_config.grid
    hybrid_plant.battery = Battery(hybrid_plant.site, config=battery_config)
    hybrid_plant.technologies["battery"] = hybrid_plant.battery
    hybrid_plant.grid = Grid(hybrid_plant.site, config=grid_config)
    hybrid_plant.technologies["grid"] = hybrid_plant.grid
    hybrid_plant.check_consistent_financial_models()
    hybrid_plant.dispatch_builder = HybridDispatchBuilderSolver(hybrid_plant.site,
                                                        hybrid_plant.technologies,
                                                        dispatch_options=hybrid_plant.dispatch_options or {})
    hybrid_plant.outputs_factory = HybridSimulationOutput(hybrid_plant.technologies)
    if len(hybrid_plant.site.elec_prices.data):
        hybrid_plant.ppa_price = 0.001
        hybrid_plant.dispatch_factors = hybrid_plant.site.elec_prices.data
    if grid_config.ppa_price:
            hybrid_plant.ppa_price = grid_config.ppa_price
    
    technology_keys = ["pv","battery","grid"]
    hybrid_plant.battery.dispatch.initialize_parameters()
    for source in technology_keys:
            hybrid_plant.technologies[source].setup_performance_model()
    
    hybrid_plant.wind._system_model.value("gen",set_value = wind_generation_profile)
    hybrid_plant.wind._system_model.value("annual_energy",set_value = np.sum(wind_generation_profile))
    hybrid_plant.wind._system_model.value("system_capacity",set_value = wind_size_mw*1e3)
    wind_cf = np.sum(wind_generation_profile) / (8760 * wind_size_mw*1e3) * 100
    hybrid_plant.wind._system_model.value("capacity_factor",set_value = wind_cf)
    hybrid_plant.wind._system_model.value("annual_energy_pre_curtailment_ac",set_value = np.sum(wind_generation_profile))
    
    hopp_results = gh_mgmt.rerun_hopp_battery(hybrid_plant,desired_schedule_kw,interconnect_kw, curtailment_value_type = "grid")

    return hopp_results
def rerun_battery_dispatch_for_new_generation_profiles(hybrid_plant:HybridSimulation, desired_schedule_kW:float, interconnection_kW:float,project_life = 20):
    lifetime_sim = False
    desired_schedule = (desired_schedule_kW/1e3)*np.ones(8760)
    
    hybrid_plant.grid.site.desired_schedule = desired_schedule
    hybrid_plant.dispatch_builder.site.desired_schedule = desired_schedule
    hybrid_plant.dispatch_builder.power_sources["grid"].site.desired_schedule = desired_schedule

    hybrid_plant.grid.interconnect_kw = interconnection_kW
    hybrid_plant.interconnect_kw = interconnection_kW
    hybrid_plant.dispatch_builder.power_sources["grid"].interconnect_kw = interconnection_kW

    hybrid_plant.dispatch_builder.simulate_power()

    non_dispatchable_systems = ['pv', 'wind','wave']
    hybrid_size_kw = 0
    hybrid_nominal_capacity = 0
    total_gen = np.zeros(hybrid_plant.site.n_timesteps * project_life)
    total_gen_before_battery = np.zeros(hybrid_plant.site.n_timesteps * project_life)
    total_gen_max_feasible_year1 = np.zeros(hybrid_plant.site.n_timesteps)
    for system in hybrid_plant.technologies.keys():
        if system != 'grid':
            model = getattr(hybrid_plant, system)
            if model:
                hybrid_size_kw += model.system_capacity_kw
                hybrid_nominal_capacity += model.calc_nominal_capacity(interconnection_kW)
                project_life_gen = np.tile(model.generation_profile, int(project_life / (len(model.generation_profile) // hybrid_plant.site.n_timesteps)))
                total_gen += project_life_gen
                if system in non_dispatchable_systems:
                    total_gen_before_battery += project_life_gen
                total_gen += project_life_gen
                model.gen_max_feasible = model.calc_gen_max_feasible_kwh(interconnection_kW)
                total_gen_max_feasible_year1 += model.gen_max_feasible

    hybrid_plant.grid.simulate_grid_connection(
            hybrid_size_kw, 
            total_gen, 
            project_life, 
            lifetime_sim,
            hybrid_plant.grid.total_gen_max_feasible_year1,
            hybrid_plant.dispatch_builder.options
        )
    hybrid_plant.grid._financial_model.value('gen', hybrid_plant.grid.generation_profile)
    hybrid_plant.grid.hybrid_nominal_capacity = hybrid_nominal_capacity
    hybrid_plant.grid.total_gen_max_feasible_year1 = total_gen_max_feasible_year1
    return hybrid_plant

def update_config_for_lcoh_delivered(config,ned_man,ned_site):
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

def update_config_for_lcoh_produced(config):
    config.greenheart_config["h2_storage"]["type"] = "none"
    onsite_plant_design_key = [k for k in config.greenheart_config["plant_design"].keys() if config.greenheart_config["plant_design"][k]["transportation"]=="colocated"]
    onsite_plant_design_key = onsite_plant_design_key[0]
    onsite_plant_design_num = int(onsite_plant_design_key.split("scenario")[-1])
    config.design_scenario = config.greenheart_config["plant_design"][onsite_plant_design_key]
    config.plant_design_scenario = onsite_plant_design_num
    return config

def get_objects_and_profiles_for_simlplex_battery(unique_wind_sizes_mw,unique_pv_sizes_mwac,ned_site,ned_man,ned_out,config,hopp_site):
    #NOTE: THIS ONLY WORKS IF RUNNING WITH FLORIS
    if len(unique_wind_sizes_mw)<len(unique_pv_sizes_mwac):
        n_extra_wind = len(unique_pv_sizes_mwac) - len(unique_wind_sizes_mw)
        extra_wind_size = np.min(unique_wind_sizes_mw)*np.ones(n_extra_wind)
        unique_wind_sizes_mw = np.concatenate((unique_wind_sizes_mw,extra_wind_size))
        slog.debug("Site {}: unique_wind_sizes_mw = {}".format(ned_site.id,unique_wind_sizes_mw))

    wind_profiles = {}
    pv_battery_hybrid_plants = {}
    # simplex_results = {}
    parametric_sweep_results = {}
    include_battery = True
    generation_tracker = {} #new
    
    delivery_keys = ["h2_pipe_array","h2_transport_compressor","h2_transport_pipeline","h2_storage"]
    # simplex_keys = ["wind_size_mw","pv_size_mwdc","battery","lcoh-delivered","lcoh-produced"]
    extra_data_keys = ["wind_size_mw","pv_size_mwdc","battery","lcoh-delivered","lcoh-produced","Electrolyzer CF","H2 Storage Size [kg]"]
    
    for ii in range(len(unique_wind_sizes_mw)):
        wind_capacity_mw = unique_wind_sizes_mw[ii]
        pv_capacity_mwac = unique_pv_sizes_mwac[ii]
        pv_capacity_mwdc = round(pv_capacity_mwac*ned_man.dc_ac_ratio,1)
        
        lcoh_delivered, hopp_results, capex_breakdown, opex_breakdown_annual, wind_cost_results, electrolyzer_physics_results, config, h2_storage_capacity = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_capacity_mw,pv_capacity_mwac,include_battery=True,output_level=8)
        # if ii==0:
        #     print("--- LCOH delivered: run 01 ---")
        #     print("wind_size_mw: {}".format(wind_capacity_mw))
        #     print("pv_size_mwdc: {}".format(pv_capacity_mwdc))
        #     print("pv_size_mwac: {}".format(pv_capacity_mwac))
        #     print("capex_breakdown:")
        #     print("\n".join("\t{}: \t{}".format(k, v) for k, v in capex_breakdown.items() if v!=0))
        #     print("opex_breakdown:")
        #     print("\n".join("\t{}: \t{}".format(k, v) for k, v in opex_breakdown_annual.items() if v!=0))
        #     print("-----------------------")
        
        wind_profiles.update({wind_capacity_mw:np.array(hopp_results["hybrid_plant"].wind.generation_profile)})
        pv_battery_hybrid_plants.update({pv_capacity_mwdc:hopp_results["hybrid_plant"]})
        
        generation_tracker.update({ii:electrolyzer_physics_results["power_to_electrolyzer_kw"]})
        
        #remove h2 storage from capex and opex breakdown
        for item in capex_breakdown.keys():
            if item in delivery_keys:
                capex_breakdown.update({item:0.0})
        for item in opex_breakdown_annual.keys():
            if item in delivery_keys:
                opex_breakdown_annual.update({item:0.0})
        config = update_config_for_lcoh_produced(config)
        []
        #calc lcoh of h2 produced
        lcoh_produced, pf_lcoh, lcoh_res = gh_mgmt.calc_offgrid_lcoh(
                hopp_results,
                capex_breakdown,
                opex_breakdown_annual,
                wind_cost_results,
                electrolyzer_physics_results,
                total_accessory_power_renewable_kw = 0.0,
                total_accessory_power_grid_kw = 0.0,
                config = config,
                )
        []
        # lcoh_tracker.append(lcoh_res) #new
        config = update_config_for_lcoh_delivered(config,ned_man,ned_site)
        
        
        # simplex_vals = [wind_capacity_mw,pv_capacity_mwdc,include_battery,lcoh_delivered,lcoh_produced]
        # simplex_results.update({ii:dict(zip(simplex_keys,simplex_vals))})

        extra_data_vals = [wind_capacity_mw,pv_capacity_mwdc,include_battery,lcoh_delivered,lcoh_produced,electrolyzer_physics_results["H2_Results"]["Life: Capacity Factor"], h2_storage_capacity]
        parametric_sweep_results.update({ii:dict(zip(extra_data_keys,extra_data_vals))})

    return wind_profiles,pv_battery_hybrid_plants, parametric_sweep_results #, generation_tracker

def loop_wind_solar_battery_designs(unique_wind_sizes_mw,unique_pv_sizes_mwac,ned_site,ned_man,ned_out,config,hopp_site,wind_profiles = None,save_detailed=True):
    interconnect_kw = ned_man.electrolyzer_size_mw*1e3
    desired_schedule_kw = interconnect_kw*config.greenheart_config["electrolyzer"]["turndown_ratio"]
    include_battery = True
    if wind_profiles is not None:
        wind_sizes_already = [k for k in list(wind_profiles.keys())]
        unique_wind_sizes_for_simplex = [k for k in unique_wind_sizes_mw if k not in wind_sizes_already]
        unique_wind_sizes_for_simplex += [np.min(unique_wind_sizes_mw)]
        unique_wind_sizes_for_simplex = np.array(unique_wind_sizes_for_simplex)
        
        wind_profiles_new,pv_battery_hybrid_plants,extra_data_results = get_objects_and_profiles_for_simlplex_battery(unique_wind_sizes_for_simplex,unique_pv_sizes_mwac,ned_site,ned_man,ned_out,config,hopp_site)
    else:
        wind_profiles = {}
        wind_profiles_new,pv_battery_hybrid_plants,extra_data_results = get_objects_and_profiles_for_simlplex_battery(unique_wind_sizes_mw,unique_pv_sizes_mwac,ned_site,ned_man,ned_out,config,hopp_site)
    wind_profiles.update(wind_profiles_new)
    #save wind generation profiles
    wind_profile_filename = "{}-{}_{}-{}--WindGenerationProfiles.pkl".format(ned_site.id,ned_site.latitude,ned_site.longitude,ned_site.state.replace(" ",""))
    wind_profile_filepath = os.path.join(ned_man.output_directory,wind_profile_filename)
    pd.Series(wind_profiles).to_pickle(wind_profile_filepath)
    slog.info("Site {}: saved wind generation profiles".format(ned_site.id,unique_wind_sizes_mw))

    cnt = max(list(extra_data_results.keys())) + 1
    #below is new
    lcoh_simplex_res = pd.DataFrame()
    lcoe_simplex_res = pd.DataFrame()
    #above is new
    # delivery_keys = ["h2_pipe_array","h2_transport_compressor","h2_transport_pipeline","h2_storage"]
    # simplex_keys = ["wind_size_mw","pv_size_mwdc","battery","lcoh-delivered","lcoh-produced"]
    extra_data_keys = ["wind_size_mw","pv_size_mwdc","battery","lcoh-delivered","lcoh-produced","Electrolyzer CF","H2 Storage Size [kg]"]
    for pi,pv_size_mwdc in enumerate(list(pv_battery_hybrid_plants.keys())):
        # print("pi: {}".format(pi))
        
        hybrid_plant = pv_battery_hybrid_plants.pop(pv_size_mwdc)
        pv_generation_profile_kwac = np.array(hybrid_plant.pv.generation_profile)
        pv_size_mwac = pv_size_mwdc/ned_man.dc_ac_ratio
        
        for wi,wind_size_mw in enumerate(wind_profiles.keys()):
            
            slog.debug("Site {}: {} MW wind, {} MWdc solar".format(ned_site.id,wind_size_mw,pv_size_mwdc))
            wind_generation_profile = wind_profiles[wind_size_mw]
            
            # ----- RUN WITH BATTERY ----- 
            hopp_results = update_hopp_for_generation_profiles(hybrid_plant,wind_size_mw,wind_generation_profile,desired_schedule_kw,interconnect_kw)
            
            hopp_results = opt_tools.update_hopp_costs_for_sizes(hopp_results,ned_man,wind_size_mw,pv_size_mwac,include_battery)
            hopp_results = gh_mgmt.update_hopp_costs(hopp_results,ned_man.atb_cost_cases_hopp[ned_man.baseline_atb_case])
            # lcoh_delivered, hopp_results, capex_breakdown, opex_breakdown_annual, wind_cost_results, electrolyzer_physics_results, config, h2_storage_capacity = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_size_mw,pv_size_mwac,include_battery=True,output_level=8,hopp_results=hopp_results)
            
            #below is new
            total_accessory_power_renewable_kw = 0.0
            total_accessory_power_grid_kw = 0.0
            re_plant_desc = "wind-pv-battery"
            capex_breakdown, opex_breakdown_annual, wind_cost_results, electrolyzer_physics_results, h2_prod_store_results, h2_transport_results, offshore_component_results = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_size_mw,pv_size_mwac,include_battery=True,output_level=9,hopp_results=hopp_results,run_lcoh=False)
            # h2_storage_capacity = h2_prod_store_results[1]["h2_storage_capacity_kg"]
            ned_out = sweep_atb_cost_cases(ned_site,ned_man,ned_out,re_plant_desc,hopp_results,electrolyzer_physics_results,h2_prod_store_results,h2_transport_results,offshore_component_results,config,total_accessory_power_renewable_kw,wind_cost_results,total_accessory_power_grid_kw,sweep_incentives = False, new_h2_storage_type = "none")
            lcoh_simplex,lcoe_simplex,ned_out = convert_ned_out_to_simplex(ned_out,wind_size_mw,pv_size_mwdc,include_battery,save_simplex_detailed=save_detailed)
            lcoh_simplex_res = pd.concat([lcoh_simplex_res,lcoh_simplex],axis=0)
            lcoe_simplex_res = pd.concat([lcoe_simplex_res,lcoe_simplex],axis=0)
            extra_data_vals = [wind_size_mw,pv_size_mwdc,include_battery,lcoh_simplex.iloc[1]["lcoh-delivered"],lcoh_simplex.iloc[1]["lcoh-produced"],electrolyzer_physics_results["H2_Results"]["Life: Capacity Factor"], h2_prod_store_results[1]["h2_storage_capacity_kg"]]
            extra_data_results.update({cnt:dict(zip(extra_data_keys,extra_data_vals))})
            cnt +=1

            # ----- RUN WITHOUT BATTERY ----- 
            re_plant_desc = "wind-pv"
            hopp_results["combined_hybrid_power_production_hopp"] =  wind_generation_profile + pv_generation_profile_kwac
            capex_breakdown, opex_breakdown_annual, wind_cost_results, electrolyzer_physics_results, h2_prod_store_results, h2_transport_results, offshore_component_results = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_size_mw,pv_size_mwac,include_battery=False,output_level=9,hopp_results=hopp_results,run_lcoh=False)
            capex_breakdown.update({"battery":0.0})
            opex_breakdown_annual.update({"battery":0.0})
            # below is new
            ned_out = sweep_atb_cost_cases(ned_site,ned_man,ned_out,re_plant_desc,hopp_results,electrolyzer_physics_results,h2_prod_store_results,h2_transport_results,offshore_component_results,config,total_accessory_power_renewable_kw,wind_cost_results,total_accessory_power_grid_kw,sweep_incentives = False, new_h2_storage_type = "none")
            lcoh_simplex_nobat,lcoe_simplex_nobat,ned_out = convert_ned_out_to_simplex(ned_out,wind_size_mw,pv_size_mwdc,False,save_simplex_detailed=save_detailed)
            lcoh_simplex_res = pd.concat([lcoh_simplex_res,lcoh_simplex_nobat],axis=0)
            lcoe_simplex_res = pd.concat([lcoe_simplex_res,lcoe_simplex_nobat],axis=0)
            # above is new
            extra_data_vals = [wind_size_mw,pv_size_mwdc,False,lcoh_simplex.iloc[1]["lcoh-delivered"],lcoh_simplex.iloc[1]["lcoh-produced"],electrolyzer_physics_results["H2_Results"]["Life: Capacity Factor"], h2_prod_store_results[1]["h2_storage_capacity_kg"]]
            extra_data_results.update({cnt:dict(zip(extra_data_keys,extra_data_vals))})
            cnt +=1

    return wind_profiles, extra_data_results, lcoh_simplex_res, lcoe_simplex_res
    # lcoh, hopp_results_battery, electrolyzer_physics_results = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_size_mw_init,pv_size_mwac_init,include_battery=True,output_level=2)
    