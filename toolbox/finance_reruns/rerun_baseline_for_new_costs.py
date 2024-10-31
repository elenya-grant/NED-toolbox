import os
from hopp.utilities import load_yaml
import yaml
import pandas as pd
from toolbox import LIB_DIR, INPUT_DIR,ROOT_DIR
from yamlinclude import YamlIncludeConstructor
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=LIB_DIR
)
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=LIB_DIR / "greenheart_hopp_config/"
)
import greenheart.tools.profast_tools as pf_tools
import greenheart.tools.eco.cost_tools as cost_tools
import toolbox.finance_reruns.profast_reverse_tools as rev_pf_tools
import ProFAST
import copy
import time
import numpy as np
import numpy_financial as npf
from toolbox.finance_reruns.finance_weighting import weight_financial_parameters_vre_h2

def combine_lcoh_physics_results(result_dir,lcoh_filenames,summary_filenames):
    h2_design_types = ["geologic_storage","onsite_storage"]
    lcoh_res = pd.DataFrame()
    physics_res = pd.DataFrame()
    for h2_design in h2_design_types:
        lcoh_fname = [f for f in lcoh_filenames if h2_design in f]
        summary_fname = [f for f in summary_filenames if h2_design in f]
        lcoh_filepath = os.path.join(result_dir,lcoh_fname[0])
        summary_filepath = os.path.join(result_dir,summary_fname[0])
        lcoh = pd.read_pickle(lcoh_filepath)
        summary = pd.read_pickle(summary_filepath)
        physics_summary = summary["Physics"]
        re_plant_designs = summary["Physics"]["renewable_plant_design_type"].to_list()
        re_plant_design_keys = ["wind_size_mw","pv_size_mwdc","battery"]
        lcoh["wind_size_mw"] = [None]*len(lcoh)
        lcoh["pv_size_mwdc"] = [None]*len(lcoh)
        lcoh["battery"] = [None]*len(lcoh)
        lcoh["battery_hours"] = [None]*len(lcoh)
        lcoh["battery_charge_rate_mw"] = [None]*len(lcoh)


        for re_plant in re_plant_designs:
            lcoh[lcoh["re_plant_type"]==re_plant]
            plant_summary = physics_summary[physics_summary["renewable_plant_design_type"]==re_plant].iloc[0]
            if "wind" in re_plant:
                wind_size_mw = plant_summary["renewables_summary"]['Wind: System Capacity [kW]']/1e3
            else:
                wind_size_mw = 0.0
            if "pv" in re_plant:
                pv_size_mwdc = plant_summary["renewables_summary"]['PV: System Capacity [kW-DC]']/1e3
            else:
                pv_size_mwdc = 0.0
            if "battery" in re_plant:
                battery = True
                battery_charge_rate_mw = plant_summary["renewables_summary"]['Battery: System Capacity [kW]']/1e3
                battery_hours = plant_summary["renewables_summary"]['Battery: System Capacity [kWh]']/plant_summary["renewables_summary"]['Battery: System Capacity [kW]']
            else:
                battery = False
                battery_hours = 0.0
                battery_charge_rate_mw = 0.0
            # re_plant_design_values = [wind_size_mw,pv_size_mwdc,battery]
            lcoh_re_plant_indx = lcoh[lcoh["re_plant_type"]==re_plant].index.to_list()
            lcoh.loc[lcoh_re_plant_indx,"wind_size_mw"] = wind_size_mw
            lcoh.loc[lcoh_re_plant_indx,"pv_size_mwdc"] = pv_size_mwdc
            lcoh.loc[lcoh_re_plant_indx,"battery"] = battery
            lcoh.loc[lcoh_re_plant_indx,"battery_hours"] = battery_hours
            lcoh.loc[lcoh_re_plant_indx,"battery_charge_rate_mw"] = battery_charge_rate_mw
        lcoh_res = pd.concat([lcoh,lcoh_res],axis=0)
        physics_res = pd.concat([physics_summary,physics_res],axis=0)
    return lcoh_res,physics_res

def make_capex_breakdown_from_pf_config(pf_config_new_capital_items):
    capex_breakdown = {}
    for capital_item in pf_config_new_capital_items.keys():
        if "h2" in capital_item.lower():
            new_capex_key = capital_item.lower().replace(" system","")
            new_capex_key = new_capex_key.replace(" ","_")
        else:
            new_capex_key = capital_item.lower().replace(" system","")
        capex_breakdown.update({new_capex_key:pf_config_new_capital_items[capital_item]["cost"]})
    return capex_breakdown

def update_itc_value(capex_breakdown,incentive_dict):
    electricity_itc_value_dollars = 0
    electricity_itc_value_percent_re_capex = incentive_dict["electricity_itc"]
    if electricity_itc_value_percent_re_capex>0:
        renewables_for_incentives = ["wind","solar","wave","electrical_export_system"]
        for item in capex_breakdown.keys():
            if any(i in item for i in renewables_for_incentives):
                electricity_itc_value_dollars += electricity_itc_value_percent_re_capex*capex_breakdown[item]  
    else:
        electricity_itc_value_dollars = 0.0
    itc_value_percent_h2_store_capex = incentive_dict["h2_storage_itc"]
    if itc_value_percent_h2_store_capex>0 and "h2_storage" in capex_breakdown:
        itc_value_dollars_h2_storage = itc_value_percent_h2_store_capex * (
            capex_breakdown["h2_storage"]
        )
    else:
        itc_value_dollars_h2_storage = 0.0

    total_itc_value = itc_value_dollars_h2_storage + electricity_itc_value_dollars

    return total_itc_value

def update_ptc_value(new_greenheart_config,incentive_dict,pf_config_new,physics_summary):
    #physics_summary = summary["Physics"]
    #NOTE: does not do H2 PTC!
    sunset_years = 10
    electricity_ptc_in_dollars_per_kw = -npf.fv(
        new_greenheart_config['finance_parameters']['costing_general_inflation'],
        new_greenheart_config["project_parameters"]["atb_year"]
        + round((pf_config_new["params"]['installation months'] / 12))
        - new_greenheart_config["finance_parameters"]["discount_years"]["electricity_ptc"],
        0,
        incentive_dict["electricity_ptc"],
    )  # given in 1992 dollars but adjust for inflation
    kw_per_kg_h2 = np.mean(np.array(physics_summary.iloc[0]["electrolyzer_LTA"]["Annual Average Efficiency [kWh/kg]"].to_list())[:sunset_years])
    electricity_ptc_in_dollars_per_kg_h2 = (
        electricity_ptc_in_dollars_per_kw * kw_per_kg_h2
    )
    if "incentives" in pf_config_new:
        pf_config_new["incentives"]["Electricity PTC"].update({"value":electricity_ptc_in_dollars_per_kg_h2})
    return pf_config_new

def run_new_costs_for_lcoh_baseline_cases(lcoh_res,physics_res,output_filename,new_atb_year,new_greenheart_config,new_atb_costs,new_hopp_costs,save_pf_config = True,weight_vre_h2_params = False, vre_h2_finance_assumptions = None):
    
    lcoh_res = lcoh_res.reset_index(drop=True)
    physics_res = physics_res.reset_index(drop=True)
    new_year_simplex = pd.DataFrame()
    merit_figure = "lcoh"
    design_simplex_keys = [k for k in lcoh_res.columns.to_list() if "lcoh" not in k]
    design_simplex_keys = [k for k in design_simplex_keys if "atb_year" not in k]
    start = time.perf_counter()
    for i in range(len(lcoh_res)):
        re_plant_desc = lcoh_res.iloc[i]["re_plant_type"]
        h2_transport_desc = lcoh_res.iloc[i]["h2_transport_design"]

        plant_physics_summary = physics_res[physics_res["re_plant_type"]==re_plant_desc]
        plant_physics_summary = plant_physics_summary[plant_physics_summary["h2_transport_type"]==h2_transport_desc]

        incentive_option = lcoh_res.iloc[i]["policy_scenario"]
        incentive_dict = new_greenheart_config["policy_parameters"][
        "option%s" % (incentive_option)]

        design_simplex = {}
        # convert pf_res into a dictionary
        pf_config_new = rev_pf_tools.convert_pf_res_to_pf_config(lcoh_res.iloc[i]["{}_pf_config".format(merit_figure)])
        pf_config_new["params"].pop("fraction of year operated")

        analysis_start_year = new_greenheart_config["finance_parameters"]["profast_config"]["params"]["analysis start year"]
        if "long term utilization" in new_greenheart_config["finance_parameters"]["profast_config"]["params"]:
            new_greenheart_config["finance_parameters"]["profast_config"]["params"].pop("long term utilization")
        if "capacity" in new_greenheart_config["finance_parameters"]["profast_config"]["params"]:
            new_greenheart_config["finance_parameters"]["profast_config"]["params"].pop("capacity")
        pf_config_new["params"].update(new_greenheart_config["finance_parameters"]["profast_config"]["params"])
        
        plant_life_years = pf_config_new["params"]["operating life"]
        installation_period_months = pf_config_new["params"]["installation months"]
        pf_config_new["params"].update({"analysis start year":analysis_start_year})
        new_years = cost_tools.create_years_of_operation(plant_life_years,analysis_start_year,installation_period_months)

        # ---- UPDATE PARAMS ----- #
        # - update years in long term utilization, 'analysis start year'
        ltu = {str(new_years[i]):v for i,v in enumerate(pf_config_new["params"]["long term utilization"].values())}
        pf_config_new["params"].update({"long term utilization":ltu})
        # ----- UPDATE CAPITAL ITEMS ---- #
        new_capex_opex_costs = copy.deepcopy(new_hopp_costs[lcoh_res.iloc[i]["atb_scenario"]])
            
        elec_capex = new_atb_costs["cost_cases"][lcoh_res.iloc[i]["atb_scenario"]]["electrolyzer"]["overnight_capex"]*new_greenheart_config["electrolyzer"]["rating"]*1e3
        elec_capex = pf_tools.adjust_dollar_year(elec_capex,new_atb_costs["electrolyzer_cost_year"],new_greenheart_config["project_parameters"]["cost_year"],new_greenheart_config["finance_parameters"]["costing_general_inflation"])
        pf_config_new["capital_items"]["Electrolyzer System"].update({"cost":elec_capex})
        
        
        # update pv capex
        if "pv" in re_plant_desc:
            solar_capex = lcoh_res.iloc[i]["pv_size_mwdc"]*new_capex_opex_costs["solar_installed_cost_mw"]
            solar_capex = pf_tools.adjust_dollar_year(solar_capex,new_atb_costs["solar_cost_year"],new_greenheart_config["project_parameters"]["cost_year"],new_greenheart_config["finance_parameters"]["costing_general_inflation"])
            pf_config_new["capital_items"]["Solar System"].update({"cost":solar_capex})
        
        # update wind capex
        if "wind" in re_plant_desc:
            wind_capex = lcoh_res.iloc[i]["wind_size_mw"]*new_capex_opex_costs["wind_installed_cost_mw"]
            wind_capex = pf_tools.adjust_dollar_year(wind_capex,new_atb_costs["wind_cost_year"],new_greenheart_config["project_parameters"]["cost_year"],new_greenheart_config["finance_parameters"]["costing_general_inflation"])
            pf_config_new["capital_items"]["Wind System"].update({"cost":wind_capex})

        # update battery capex
        if lcoh_res.iloc[i]["battery"]:
            lcoh_res.iloc[i]["battery_hours"]
            battery_capex_pr_mw = new_capex_opex_costs["storage_installed_cost_mw"] + (lcoh_res.iloc[i]["battery_hours"]*new_capex_opex_costs["storage_installed_cost_mwh"])
            battery_capex = battery_capex_pr_mw*lcoh_res.iloc[i]["battery_charge_rate_mw"]
            battery_capex = pf_tools.adjust_dollar_year(battery_capex,new_atb_costs["battery_cost_year"],new_greenheart_config["project_parameters"]["cost_year"],new_greenheart_config["finance_parameters"]["costing_general_inflation"])
            pf_config_new["capital_items"]["Battery System"].update({"cost":battery_capex})
        # make capex breakdown
        capex_breakdown = make_capex_breakdown_from_pf_config(pf_config_new["capital_items"])
        
        #update financial parameters if using the weighted option
        if weight_vre_h2_params:
            pf_config_new = weight_financial_parameters_vre_h2(capex_breakdown,vre_h2_finance_assumptions,pf_config_new)
        # ----- UPDATE FIXED COSTS ---- #
        if "pv" in re_plant_desc:
            pv_fom = new_capex_opex_costs["pv_om_per_kw"]*lcoh_res.iloc[i]["pv_size_mwdc"]*1e3
            pv_fom = pf_tools.adjust_dollar_year(pv_fom,new_atb_costs["solar_cost_year"],new_greenheart_config["project_parameters"]["cost_year"],new_greenheart_config["finance_parameters"]["costing_general_inflation"])
            pf_config_new["fixed_costs"]["Solar O&M Cost"].update({"cost":pv_fom})

        if "wind" in re_plant_desc:
            wind_fom = new_capex_opex_costs["wind_om_per_kw"]*lcoh_res.iloc[i]["wind_size_mw"]*1e3
            wind_fom = pf_tools.adjust_dollar_year(wind_fom,new_atb_costs["wind_cost_year"],new_greenheart_config["project_parameters"]["cost_year"],new_greenheart_config["finance_parameters"]["costing_general_inflation"])

            pf_config_new["fixed_costs"]["Wind And Electrical O&M Cost"].update({"cost":wind_fom})

        if lcoh_res.iloc[i]["battery"]:
            battery_fom = new_capex_opex_costs["battery_om_per_kw"]*lcoh_res.iloc[i]["battery_charge_rate_mw"]*1e3
            battery_fom = pf_tools.adjust_dollar_year(battery_fom,new_atb_costs["battery_cost_year"],new_greenheart_config["project_parameters"]["cost_year"],new_greenheart_config["finance_parameters"]["costing_general_inflation"])
            pf_config_new["fixed_costs"]["Battery O&M Cost"].update({"cost":battery_fom})
        
        elec_fom = new_atb_costs["cost_cases"][lcoh_res.iloc[i]["atb_scenario"]]["electrolyzer"]["fixed_om"]*new_greenheart_config["electrolyzer"]["rating"]*1e3
        elec_fom = pf_tools.adjust_dollar_year(elec_fom,new_atb_costs["electrolyzer_cost_year"],new_greenheart_config["project_parameters"]["cost_year"],new_greenheart_config["finance_parameters"]["costing_general_inflation"])
        pf_config_new["fixed_costs"]["Electrolyzer O&M Cost"].update({"cost":elec_fom})
        
        # ----- UPDATE FEEDSTOCK COSTS ---- #
        elec_varom = {str(new_years[i]):v for i,v in enumerate(pf_config_new["feedstocks"]["Electrolyzer Variable O&M"]["cost"].values())}
        pf_config_new["feedstocks"]["Electrolyzer Variable O&M"].update({"cost":elec_varom})

        # ----- UPDATE ITC VALUE ---- #
        if pf_config_new['params']["one time cap inct"]["value"]>0:
            itc_value = update_itc_value(capex_breakdown,incentive_dict)
            pf_config_new['params']["one time cap inct"].update({"value":itc_value})
        # ----- UPDATE PTC VALUE ---- #
        if pf_config_new["incentives"]["Electricity PTC"]["value"]>0:
            pf_config_new = update_ptc_value(new_greenheart_config,incentive_dict,pf_config_new,plant_physics_summary)


        pf = pf_tools.create_and_populate_profast(pf_config_new)
        sol,summary,price_breakdown = pf_tools.run_profast(pf)
        lcoh = sol["price"]
        design_simplex.update({merit_figure:lcoh})
        lcoh_pf_config = {"params":pf.vals,
        "capital_items":pf.capital_items,
        "fixed_costs":pf.fixed_costs,
        "feedstocks":pf.feedstocks,
        "incentives":pf.incentives,
        "LCOH":pf.LCO}
        design_simplex.update({"{}_pf_config".format(merit_figure):dict(lcoh_pf_config)})
        design_simplex.update(lcoh_res.iloc[i][design_simplex_keys].to_dict())
        design_simplex.update({"atb_year":new_atb_year})
        temp_df = pd.Series(design_simplex,name=i)
        new_year_simplex = pd.concat([new_year_simplex,temp_df],axis=1)

    
    if save_pf_config:
        ordered_cols = lcoh_res.columns.to_list()
    else:
        ordered_cols = [c for c in lcoh_res.columns.to_list() if "pf_config" not in c]
    if output_filename is not None:
        new_year_simplex.T[ordered_cols].to_pickle(output_filename)
    end = time.perf_counter()
    sim_time = (end - start)/60
    print("Took {} min to run costs for new year".format(round(sim_time,2)))
    return new_year_simplex.T
