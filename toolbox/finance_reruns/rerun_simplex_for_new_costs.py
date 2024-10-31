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
from toolbox.finance_reruns.finance_weighting import weight_financial_parameters_vre_h2
def run_new_costs_for_lcoh_simplex(new_results_dir,new_atb_year,battery_charge_rate_mw,battery_hours,simplex_filepath,greenheart_config,atb_costs,hopp_costs,save_pf_config = True,weight_vre_h2_params = False, vre_h2_finance_assumptions = None):
    simplex_fname = simplex_filepath.split("/")[-1]
    output_filename = os.path.join(new_results_dir,simplex_fname)
    
    simplex = pd.read_pickle(simplex_filepath)
    simplex = simplex.reset_index(drop=True)

    new_year_simplex = pd.DataFrame()
    merit_figures = ["lcoh-produced","lcoh-delivered"]
    design_simplex_keys = [k for k in simplex.columns.to_list() if "lcoh" not in k]
    design_simplex_keys = [k for k in design_simplex_keys if "atb_year" not in k]
    start = time.perf_counter()
    for i in range(len(simplex)):
        design_simplex = {}
        for merit_figure in merit_figures:
            pf_config_new = rev_pf_tools.convert_pf_res_to_pf_config(simplex.iloc[i]["{}_pf_config".format(merit_figure)])
            pf_config_new["params"].pop("fraction of year operated")

            analysis_start_year = new_atb_year + 2
            if "long term utilization" in greenheart_config["finance_parameters"]["profast_config"]["params"]:
                greenheart_config["finance_parameters"]["profast_config"]["params"].pop("long term utilization")
            if "capacity" in greenheart_config["finance_parameters"]["profast_config"]["params"]:
                greenheart_config["finance_parameters"]["profast_config"]["params"].pop("capacity")
            pf_config_new["params"].update(greenheart_config["finance_parameters"]["profast_config"]["params"])
            plant_life_years = pf_config_new["params"]["operating life"]
            installation_period_months = pf_config_new["params"]["installation months"]
            pf_config_new["params"].update({"analysis start year":analysis_start_year})
            new_years = cost_tools.create_years_of_operation(plant_life_years,analysis_start_year,installation_period_months)

            # ---- UPDATE PARAMS ----- #
            # - update years in long term utilization, 'analysis start year'
            ltu = {str(new_years[i]):v for i,v in enumerate(pf_config_new["params"]["long term utilization"].values())}
            pf_config_new["params"].update({"long term utilization":ltu})
            # ----- UPDATE CAPITAL ITEMS ---- #
            new_capex_opex_costs = copy.deepcopy(hopp_costs[simplex.iloc[i]["atb_scenario"]])
                
            elec_capex = atb_costs["cost_cases"][simplex.iloc[i]["atb_scenario"]]["electrolyzer"]["overnight_capex"]*greenheart_config["electrolyzer"]["rating"]*1e3
            elec_capex = pf_tools.adjust_dollar_year(elec_capex,atb_costs["electrolyzer_cost_year"],greenheart_config["project_parameters"]["cost_year"],greenheart_config["finance_parameters"]["costing_general_inflation"])
            pf_config_new["capital_items"]["Electrolyzer System"].update({"cost":elec_capex})

            solar_capex = simplex.iloc[i]["pv_size_mwdc"]*new_capex_opex_costs["solar_installed_cost_mw"]
            solar_capex = pf_tools.adjust_dollar_year(solar_capex,atb_costs["solar_cost_year"],greenheart_config["project_parameters"]["cost_year"],greenheart_config["finance_parameters"]["costing_general_inflation"])
            pf_config_new["capital_items"]["Solar System"].update({"cost":solar_capex})

            wind_capex = simplex.iloc[i]["wind_size_mw"]*new_capex_opex_costs["wind_installed_cost_mw"]
            wind_capex = pf_tools.adjust_dollar_year(wind_capex,atb_costs["wind_cost_year"],greenheart_config["project_parameters"]["cost_year"],greenheart_config["finance_parameters"]["costing_general_inflation"])
            pf_config_new["capital_items"]["Wind System"].update({"cost":wind_capex})

            if simplex.iloc[i]["battery"]:
                battery_capex_pr_mw = new_capex_opex_costs["storage_installed_cost_mw"] + (battery_hours*new_capex_opex_costs["storage_installed_cost_mwh"])
                battery_capex = battery_capex_pr_mw*battery_charge_rate_mw
                battery_capex = pf_tools.adjust_dollar_year(battery_capex,atb_costs["battery_cost_year"],greenheart_config["project_parameters"]["cost_year"],greenheart_config["finance_parameters"]["costing_general_inflation"])
                pf_config_new["capital_items"]["Battery System"].update({"cost":battery_capex})

            # ----- UPDATE FIXED COSTS ---- #
            pv_fom = new_capex_opex_costs["pv_om_per_kw"]*simplex.iloc[i]["pv_size_mwdc"]*1e3
            pv_fom = pf_tools.adjust_dollar_year(pv_fom,atb_costs["solar_cost_year"],greenheart_config["project_parameters"]["cost_year"],greenheart_config["finance_parameters"]["costing_general_inflation"])
            pf_config_new["fixed_costs"]["Solar O&M Cost"].update({"cost":pv_fom})

            wind_fom = new_capex_opex_costs["wind_om_per_kw"]*simplex.iloc[i]["wind_size_mw"]*1e3
            wind_fom = pf_tools.adjust_dollar_year(wind_fom,atb_costs["wind_cost_year"],greenheart_config["project_parameters"]["cost_year"],greenheart_config["finance_parameters"]["costing_general_inflation"])

            pf_config_new["fixed_costs"]["Wind And Electrical O&M Cost"].update({"cost":wind_fom})

            if simplex.iloc[i]["battery"]:
                battery_fom = new_capex_opex_costs["battery_om_per_kw"]*battery_charge_rate_mw*1e3
                battery_fom = pf_tools.adjust_dollar_year(battery_fom,atb_costs["battery_cost_year"],greenheart_config["project_parameters"]["cost_year"],greenheart_config["finance_parameters"]["costing_general_inflation"])
                pf_config_new["fixed_costs"]["Battery O&M Cost"].update({"cost":battery_fom})
            
            elec_fom = atb_costs["cost_cases"][simplex.iloc[i]["atb_scenario"]]["electrolyzer"]["fixed_om"]*greenheart_config["electrolyzer"]["rating"]*1e3
            elec_fom = pf_tools.adjust_dollar_year(elec_fom,atb_costs["electrolyzer_cost_year"],greenheart_config["project_parameters"]["cost_year"],greenheart_config["finance_parameters"]["costing_general_inflation"])
            pf_config_new["fixed_costs"]["Electrolyzer O&M Cost"].update({"cost":elec_fom})
            # ----- UPDATE FEEDSTOCK COSTS ---- #
            elec_varom = {str(new_years[i]):v for i,v in enumerate(pf_config_new["feedstocks"]["Electrolyzer Variable O&M"]["cost"].values())}
            pf_config_new["feedstocks"]["Electrolyzer Variable O&M"].update({"cost":elec_varom})

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
        design_simplex.update(simplex.iloc[i][design_simplex_keys].to_dict())
        design_simplex.update({"atb_year":new_atb_year})
        temp_df = pd.Series(design_simplex,name=i)
        new_year_simplex = pd.concat([new_year_simplex,temp_df],axis=1)

    
    if save_pf_config:
        ordered_cols = simplex.columns.to_list()
    else:
        ordered_cols = [c for c in simplex.columns.to_list() if "pf_config" not in c]
    new_year_simplex.T[ordered_cols].to_pickle(output_filename)
    end = time.perf_counter()
    sim_time = (end - start)/60
    # print("Took {} min to run costs for new year".format(round(sim_time,2)))
    return new_year_simplex.T

# if __name__ == "__main__":

#     site_id = 14740

#     battery_charge_rate_mw = 100
#     battery_hours = 4

#     previous_sweep_name = "offgrid-optimized"
#     previous_subsweep_name = "hybrid_renewables"
#     previous_ATB_year = 2025
#     new_atb_year = 2030
#     #below is for local results
#     previous_results_dir = os.path.join(ROOT_DIR,"results",previous_sweep_name,previous_subsweep_name,"ATB_{}".format(previous_ATB_year))
#     new_results_dir = os.path.join(ROOT_DIR,"results",previous_sweep_name,previous_subsweep_name,"ATB_{}".format(new_atb_year))
#     #below is for HPC results
#     # results_main_dir_hpc = "/projects/hopp/ned-results/v1"
#     # previous_results_dir = os.path.join(results_main_dir_hpc,previous_sweep_name,previous_subsweep_name,"ATB_{}".format(previous_ATB_year))
#     # new_results_dir = os.path.join(results_main_dir_hpc,previous_sweep_name,previous_subsweep_name,"ATB_{}".format(new_atb_year))
    
#     if not os.path.isdir(new_results_dir):
#         os.makedirs(new_results_dir,exist_ok=True)
    
#     #get simplex filename
#     res_files = os.listdir(previous_results_dir)
#     site_files = [f for f in res_files if f.split("-")[0]==str(site_id)]
#     simplex_file = [f for f in site_files if "LCOH_Simplex.pkl" in f]
#     simplex_filepath = os.path.join(previous_results_dir,simplex_file[0])
#     simplex = pd.read_pickle(simplex_filepath)
#     simplex = simplex.reset_index(drop=True)

#     finance_dir = os.path.join(str(LIB_DIR),"finance")
#     greenheart_dir = os.path.join(str(LIB_DIR),"greenheart_hopp_config")
    
#     new_atb_cost_filename = os.path.join(finance_dir,"ATB2024_technology_cost_cases_2022USD_{}.yaml".format(new_atb_year))
#     new_hopp_cost_filename = os.path.join(finance_dir,"hopp_cost_info_{}.yaml".format(new_atb_year))
#     greenheart_config_filename = os.path.join(greenheart_dir,"greenheart_config_onshore_template_atb2022.yaml")
    
#     greenheart_config = load_yaml(greenheart_config_filename)
#     atb_costs = load_yaml(new_atb_cost_filename)
#     hopp_costs = load_yaml(new_hopp_cost_filename)

#     run_new_costs_for_lcoh_simplex(new_results_dir,new_atb_year,battery_charge_rate_mw,battery_hours,simplex_filepath,greenheart_config,atb_costs,hopp_costs)
