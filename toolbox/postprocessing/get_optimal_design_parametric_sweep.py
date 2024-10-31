
import pandas as pd
import numpy as np
import os
from toolbox.utilities.file_tools import check_create_folder
from datetime import datetime
import sys
from mpi4py import MPI
def find_min_lcoh_for_param_sweep(filelist,results_dir,output_filename_base):
    summary_df = pd.DataFrame()
    site_keys = ["id","latitude","longitude","state"]
    # index_keys = site_keys + ["RE Plant Design","ATB Scenario","Merit Figure"]
    index_keys = ["RE Plant Design","ATB Scenario","Merit Figure"] #,"state","id"]
    atb_cost_scenarios = ["Conservative","Moderate","Advanced"]
    battery_opt = [True, False]
    merit_figures = ["lcoh-delivered","lcoh-produced"]
    for ii,file in enumerate(filelist):
        filepath = os.path.join(results_dir,file)
        site_desc = file.split("--")[0]
        site_id = site_desc.split("-")[0]
        state = site_desc.split("-")[-1]
        lat = site_desc.split("-")[1].replace("_","")
        lon = site_desc.split("_")[-1].replace("-{}".format(state),"")
        site_vals = [int(site_id),float(lat),float(lon),state]

        simplex = pd.read_pickle(filepath)
        drop_cols = [k for k in simplex.columns.to_list() if "pf_config" in k]
        simplex = simplex.drop(columns = drop_cols)
        simplex = simplex.reset_index(drop=True)
        site_opt_designs = pd.DataFrame()
        for atb_scenario in atb_cost_scenarios:
            for battery in battery_opt:
                if battery:
                    re_plant_desc = "wind-pv-battery"
                else:
                    re_plant_desc = "wind-pv"
                for merit_figure in merit_figures:
                    opt_design_dict = dict(zip(site_keys,site_vals))
                    a = simplex[simplex["atb_scenario"]==atb_scenario]
                    a = a[a["battery"]==battery]
                    i_min = a[merit_figure].idxmin()
                    
                    optimal_design = a.loc[i_min].to_dict()
                    opt_design_dict.update(optimal_design)

                    index_vals = [re_plant_desc,atb_scenario,merit_figure] #,state,int(site_id)]
                    index_dict = dict(zip(index_keys,index_vals))
                    opt_design_dict.update(index_dict)

                    res_temp = pd.DataFrame(opt_design_dict,index=[0])
                    res_temp = res_temp.set_index(index_keys + ["state","id"])
                    site_opt_designs = pd.concat([site_opt_designs,res_temp],axis=0)
        summary_df = pd.concat([summary_df,site_opt_designs],axis=0)
    summary_df.to_pickle(output_filename_base + ".pkl")
    summary_df.to_csv(output_filename_base + ".csv")
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
    version = 1
    sweep_name = "offgrid-optimized"
    subsweep_name = "hybrid_renewables"
    atb_year = 2030
    result_dir = "/projects/hopp/ned-results/v{}/{}/{}/ATB_{}".format(version,sweep_name,subsweep_name,atb_year)
    summary_dir = "/projects/hopp/ned-results/v{}/aggregated_results".format(version)
    check_create_folder(summary_dir)
    
    res_files = os.listdir(result_dir)
    result_type = "Summary"
    file_ext = ".pkl"

    summary_files = [f for f in res_files if result_type in f]
    summary_files = [f for f in summary_files if file_ext in f]

    file_desc = "ParamSweep_OptimalResults_{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)
    filepath = os.path.join(summary_dir,file_desc)
    main(summary_files,result_dir,filepath)