import pandas as pd
import os
import numpy as np
# df = df.sort_index(axis=0,level="id")
from toolbox.tools.environment_tools import set_local_results_dir_dot_env
from toolbox.tools.environment_tools import get_local_results_dir
def find_min_max_for_site(site_df,site_id):
    re_plant_types = ["wind-pv","wind-pv-battery"]
    merit_figures = ["lcoh-delivered","lcoh-produced"]
    atb_cost_scenarios = ["Conservative","Moderate","Advanced"]
    index_keys = ["RE Plant Design","ATB Scenario","Merit Figure"]
    state = site_df.index.to_list()[0]
    site_opt_designs = pd.DataFrame()
    for atb_scenario in atb_cost_scenarios:
        for re_plant_desc in re_plant_types:
            for merit_figure in merit_figures:
                index_vals = [re_plant_desc,atb_scenario,merit_figure] #,state,int(site_id)]
                index_dict = dict(zip(index_keys,index_vals))
                a = site_df[site_df["atb_scenario"]==atb_scenario]
                a = a[a["re_plant_type"]==re_plant_desc]
                a = a.reset_index(drop=True)
                i_min = np.argmin(a[merit_figure].to_list())
                # i_min = a[merit_figure].idxmin()
                optimal_design = a.iloc[i_min].to_dict()
                optimal_design.update({"id":site_id})
                optimal_design.update({"state":state})
                optimal_design.update(index_dict)
                res_temp = pd.DataFrame(optimal_design,index=[0])
                res_temp = res_temp.set_index(index_keys + ["state","id"])
                site_opt_designs = pd.concat([site_opt_designs,res_temp],axis=0)
    return site_opt_designs

def find_min_lcoh_for_param_sweep(full_lcoh_simplex_data,site_id_list):
    summary_df = pd.DataFrame()
    
    for site_id in site_id_list:
        site_opt_designs = find_min_max_for_site(full_lcoh_simplex_data.loc[site_id],site_id)
        summary_df = pd.concat([summary_df,site_opt_designs],axis=0)
    return summary_df
    # summary_df.to_pickle(output_filename_base + ".pkl")
    # summary_df.to_csv(output_filename_base + ".csv")
    # print("saved {}".format(output_filename_base))
version = "v1"
atb_year = 2030
AGG_RES_DIR = "/projects/hopp/ned-results/{}/aggregated_results".format(version)
ip_filetype = "pkl"
sweep_name = "offgrid-optimized"
subsweep_name = "hybrid_renewables" #"under-sized" #"equal-sized"
weighted = False
if weighted:
    atb_fin_desc = "ATB_{}_weighted".format(atb_year)
else:
    atb_fin_desc = "ATB_{}".format(atb_year)
optimal_design_results_filename_dirty = os.path.join(AGG_RES_DIR,"OptimalDesigns_ParamSweep_{}_{}_{}_{}.pkl".format(version,sweep_name,subsweep_name,atb_fin_desc))
# optimal_design_results_filename_clean = os.path.join(CLEAN_RES_DIR,"Clean-OptimalDesigns_ParamSweep_{}_{}_{}_{}.pkl".format(version,sweep_name,subsweep_name,atb_fin_desc))
if os.path.isfile(optimal_design_results_filename_dirty):
    optimal_designs = pd.read_pickle(optimal_design_results_filename_dirty)
else:
    files = os.listdir(AGG_RES_DIR)
    files = [f for f in files if sweep_name in f]
    files = [f for f in files if subsweep_name in f]
    files = [f for f in files if str(atb_year) in f]
    files = [f for f in files if ip_filetype in f]
    files = [f for f in files if "Results--" in f]
    files = [f for f in files if "OptimalDesigns_" not in f]

    data_type = "LCOH"
    data_files = [f for f in files if data_type in f]
    data = pd.read_pickle(os.path.join(AGG_RES_DIR,data_files[0]))
    data = data.drop_duplicates()
    data = data.sort_index(axis=0,level="id")
    data = data.swaplevel("state","id")
    sitelist_ids = data.reset_index(level="id")["id"].to_list()
    sitelist_ids = np.unique(sitelist_ids)
    optimal_designs = find_min_lcoh_for_param_sweep(data,sitelist_ids)
    optimal_designs.to_pickle(optimal_design_results_filename_dirty)
    print("optimal designs is length {}".format(len(optimal_designs))) #should be 600984
    print("saved optimal design results to:")
    print(optimal_design_results_filename_dirty)
# if os.path.isfile(optimal_design_results_filename_clean):
#     clean_optimal_designs = pd.read_pickle(optimal_design_results_filename_clean)
# else:
#     clean_optimal_designs = reformat_optimal_results_to_baseline_case(optimal_designs)
#     clean_optimal_designs.to_pickle(optimal_design_results_filename_clean)
print("Done")

# print(data.columns.to_list())
# print("data is {} long".format(len(data.drop_duplicates())))
# merit_figures = ["lcoh-produced","lcoh-delivered"]
