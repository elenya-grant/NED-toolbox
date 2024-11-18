import pandas as pd
import os
import numpy as np
import time
import sys
from mpi4py import MPI
import datetime
import faulthandler
faulthandler.enable()
# df = df.sort_index(axis=0,level="id")
# from toolbox.tools.environment_tools import set_local_results_dir_dot_env
# from toolbox.tools.environment_tools import get_local_results_dir
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


def run_cleaning_for_param_sweep(summary_dir,run_desc,run_id,result_type="LCOH_Simplex"):
    # if not os.path.isdir(summary_dir):
    #     os.makedirs(summary_dir)
    if isinstance(run_id,list):
        run_id = run_id[0]

    ip_filetype = "pkl"
    optimal_design_results_filename_dirty = os.path.join(summary_dir,"OptimalDesigns_ParamSweep_{}_{}_{}.pkl".format(result_type,run_desc,run_id))
    # optimal_design_results_filename_dirty = os.path.join(summary_dir,"Results--OptimalDesigns_ParamSweep_{}_{}_{}_{}.pkl".format(electrolyzer_capex_version,sweep_name,subsweep_name,atb_fin_desc))
    # optimal_design_results_filename_clean = os.path.join(summary_dir,"Clean-OptimalDesigns_ParamSweep_{}_{}_{}_{}.pkl".format(electrolyzer_capex_version,sweep_name,subsweep_name,atb_fin_desc))
    # if os.path.isfile(optimal_design_results_filename_dirty):
    #     optimal_designs = pd.read_pickle(optimal_design_results_filename_dirty)
    # else:
    # start = time.perf_counter()
    # files = os.listdir(summary_dir)
    summary_type = "FullParamSweep_{}".format(result_type)
    data_filename = "{}_{}_{}.{}".format(summary_type,run_desc,run_id,ip_filetype)
    data = pd.read_pickle(os.path.join(summary_dir,data_filename))
    data = data.drop_duplicates()
    data = data.sort_index(axis=0,level="id")
    data = data.swaplevel("state","id")
    sitelist_ids = data.reset_index(level="id")["id"].to_list()
    sitelist_ids = np.unique(sitelist_ids)
    optimal_designs = find_min_lcoh_for_param_sweep(data,sitelist_ids)
    optimal_designs.to_pickle(optimal_design_results_filename_dirty)
    # end = time.perf_counter()
    # sim_time = round(((end-start)/60),2)
    # print("optimal designs is length {}".format(len(optimal_designs))) #should be 600984
    # print("took {} minutes".format(sim_time))
start_time = datetime.now()

comm = MPI.COMM_WORLD
size = MPI.COMM_WORLD.Get_size()
rank = MPI.COMM_WORLD.Get_rank()
name = MPI.Get_processor_name()

def main(run_id_list,summary_dir,run_desc):
    if rank == 0:
        print(" i'm rank {}:".format(rank))
        ################################ split site_idx's
        s_list = run_id_list
        # check if number of ranks <= number of tasks
        if size > len(s_list):
            print(
                "number of scenarios {} < number of ranks {}, abborting...".format(
                    len(s_list), size
                )
            )
            sys.exit()

        # split them into chunks (number of chunks = number of ranks)
        chunk_size = len(s_list) // size

        remainder_size = len(s_list) % size

        s_list_chunks = [
            s_list[i : i + chunk_size] for i in range(0, size * chunk_size, chunk_size)
        ]
        # distribute remainder to chunks
        for i in range(-remainder_size, 0):
            s_list_chunks[i].append(s_list[i])
        # distribute remainder to chunks
        for i in range(-remainder_size, 0):
            s_list_chunks[i].append(s_list[i])
    else:
        s_list_chunks = None
    ### scatter
    s_list_chunks = comm.scatter(s_list_chunks, root=0)
    print(f"\n rank {rank} has its files to process")
    # for i,gid in enumerate(s_list_chunks):
    run_cleaning_for_param_sweep(summary_dir,run_desc,s_list_chunks)
    # find_min_lcoh_for_param_sweep(s_list_chunks,result_dir,output_filepath_base_base + f"_{rank}")
    print(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")



if __name__=="__main__":
    # versions = ["v1_custom","v1_oldGS"]
    # atb_years = [2025,2030]
    # for ii in range(len(versions)):
    #     run_cleaning_for_param_sweep(versions[ii],atb_years[ii])
    # print("Done")

    if len(sys.argv)<3:
        electrolyzer_capex_version = "v1"
        atb_year = 2025
        finance_case = None
    else:
        electrolyzer_capex_version =  sys.argv[1]
        atb_year = int(sys.argv[2])
        if len(sys.argv)>3:
            finance_case = sys.argv[3]
        else:
            finance_case = None

    sweep_name = "offgrid-optimized"
    subsweep_name = "hybrid_renewables"
    result_type = "LCOH_Simplex"

    electrolyzer_capex_versions = ["v1","v1_custom","v1_pathway"]
    if finance_case is None:
        run_desc = "{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)
    else:
        run_desc = "{}_{}_ATB_{}_{}".format(sweep_name,subsweep_name,atb_year,finance_case)
    
    n_files = 20
    run_id_lst = np.arange(0,n_files,1)
    run_id_lst = [str(int(rid)) for rid in run_id_lst]

    summary_dir = "/projects/hopp/ned-results/{}/aggregated_results".format(electrolyzer_capex_version)
    # run_cleaning_for_param_sweep(summary_dir,run_desc,result_type=result_type)
    main(run_id_lst,summary_dir,run_desc)
    