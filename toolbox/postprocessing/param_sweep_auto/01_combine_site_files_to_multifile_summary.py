
import pandas as pd
import numpy as np
import os
from toolbox.utilities.file_tools import check_create_folder
from datetime import datetime
import sys
from mpi4py import MPI
def find_min_lcoh_for_param_sweep(filelist,results_dir,output_filename_base):
    summary_df = pd.DataFrame()
    # site_keys = ["id","latitude","longitude","state"]
    # index_keys = ["RE Plant Design","ATB Scenario","Merit Figure"] #,"state","id"]
    # atb_cost_scenarios = ["Conservative","Moderate","Advanced"]
    # battery_opt = [True, False]
    # merit_figures = ["lcoh-delivered","lcoh-produced"]
    for ii,file in enumerate(filelist):
        filepath = os.path.join(results_dir,file)
        site_desc = file.split("--")[0]
        site_id = site_desc.split("-")[0]
        state = site_desc.split("-")[-1]
        lat = site_desc.split("-")[1].replace("_","")
        lon = site_desc.split("_")[-1].replace("-{}".format(state),"")
        # site_vals = [int(site_id),float(lat),float(lon),state]

        simplex = pd.read_pickle(filepath)
        drop_cols = [k for k in simplex.columns.to_list() if "pf_config" in k]
        if len(drop_cols)>0:
            simplex = simplex.drop(columns = drop_cols)
        simplex = simplex.reset_index(drop=True)
        # index_dict = dict(zip(index_keys,index_vals))
        simplex["id"] = int(site_id)
        simplex["latitude"] = float(lat)
        simplex["longitude"] = float(lon)
        simplex["state"] = state
        
        simplex = simplex.set_index(["state","id"])
        
        summary_df = pd.concat([summary_df,simplex],axis=0)
    summary_df.to_pickle(output_filename_base + ".pkl")
    # summary_df.to_csv(output_filename_base + ".csv")
    print("saved {}".format(output_filename_base))

start_time = datetime.now()

comm = MPI.COMM_WORLD
size = MPI.COMM_WORLD.Get_size()
rank = MPI.COMM_WORLD.Get_rank()
name = MPI.Get_processor_name()

def main(full_filelist,result_dir,output_filepath_base_base):
    if rank == 0:
        print(" i'm rank {}:".format(rank))
        ################################ split site_idx's
        s_list = full_filelist
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
    find_min_lcoh_for_param_sweep(s_list_chunks,result_dir,output_filepath_base_base + f"_{rank}")
    print(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")


if __name__ == "__main__":
    # from toolbox import ROOT_DIR, LIB_DIR
    # -------- IF KESTREL --------
    #code NED-toolbox/toolbox/postprocessing/aggregate_data/aggregate_param_sweep_results_parallel.py
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
    if finance_case is None:
        site_result_dir = "/projects/hopp/ned-results/{}/{}/{}/ATB_{}".format(electrolyzer_capex_version,sweep_name,subsweep_name,atb_year)
        file_desc = "FullParamSweep_{}_{}_{}_ATB_{}".format(result_type,sweep_name,subsweep_name,atb_year)
    else:
        site_result_dir = "/projects/hopp/ned-results/{}/{}/{}/ATB_{}/{}".format(electrolyzer_capex_version,sweep_name,subsweep_name,atb_year,finance_case)
        file_desc = "FullParamSweep_{}_{}_{}_ATB_{}_{}".format(result_type,sweep_name,subsweep_name,atb_year,finance_case)
    
    summary_dir = "/projects/hopp/ned-results/{}/aggregated_results".format(electrolyzer_capex_version)
    check_create_folder(summary_dir)
    
    res_files = os.listdir(site_result_dir)
    # result_type = "LCOH_Simplex"
    file_ext = ".pkl"

    summary_files = [f for f in res_files if result_type in f]
    summary_files = [f for f in summary_files if file_ext in f]

    
    filepath = os.path.join(summary_dir,file_desc)
    main(summary_files,site_result_dir,filepath)