import pandas as pd
import numpy as np
import os
from toolbox.utilities.file_tools import check_create_folder
from datetime import datetime
import sys
from mpi4py import MPI

def aggregate_files(filelist,results_dir,output_filename_base):
    summary_df = pd.DataFrame()
    site_keys = ["id","latitude","longitude","state"]
    index_keys = site_keys + ["RE Plant Design"]
    for ii,file in enumerate(filelist):
        filepath = os.path.join(results_dir,file)
        df = pd.read_pickle(filepath)
        init_index_vals = df["Site"][site_keys].to_list()

        cost_descriptions = ["LCOE [$/kWh]: {}-{}-Policy#{}".format(df["LCOE"].iloc[i]["atb_year"],df["LCOE"].iloc[i]["atb_scenario"],df["LCOE"].iloc[i]["policy_scenario"]) for i in range(len(df["LCOE"]))]
        
        unique_re_plant_types = list(np.unique(df["LCOE"]["re_plant_type"]))
        
        df["LCOE"]["Cost Scenario"] = cost_descriptions
        
        lcoe_df = df["LCOE"].drop(columns = ["atb_year","atb_scenario","policy_scenario"])
        lcoe_df.index = [df["LCOE"]["re_plant_type"]]
        lcoe_df = lcoe_df.drop(columns = ["re_plant_type"])
        reformatted_lcoe_df = pd.DataFrame()
        for re_plant in unique_re_plant_types:
            lcoe_df.loc[re_plant]
            index = init_index_vals + [re_plant]
            index = [[k] for k in index]
            lcoe_vals = lcoe_df.loc[re_plant]["lcoe"].to_list()
            columns = lcoe_df.loc[re_plant]["Cost Scenario"].to_list()
            lcoe_temp = pd.DataFrame(dict(zip(columns,lcoe_vals)),index = [0])
            lcoe_temp.index = index
            reformatted_lcoe_df = pd.concat([lcoe_temp,reformatted_lcoe_df],axis=0)
        reformatted_lcoe_df.index = reformatted_lcoe_df.index.set_names(index_keys)
        summary_df = pd.concat([summary_df,reformatted_lcoe_df],axis=0)
    summary_df.to_pickle(output_filename_base + ".pkl")
    summary_df.to_csv(output_filename_base + ".pkl")

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

    # for i,gid in enumerate(s_list_chunks):
    aggregate_files(s_list_chunks,result_dir,output_filepath_base_base + f"_{rank}")
    print(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")


if __name__ == "__main__":
    # from toolbox import ROOT_DIR, LIB_DIR
    # -------- IF KESTREL --------
    version = 1
    sweep_name = "offgrid-baseline"
    subsweep_name = "equal-sized"
    atb_year = 2030
    result_dir = "/projects/hopp/ned-results/v{}/{}/{}/ATB_{}".format(version,sweep_name,subsweep_name,atb_year)
    summary_dir = "/projects/hopp/ned-results/v{}/aggregated_results".format(version)
    check_create_folder(summary_dir)

    file_desc = "LCOE_{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)
    filepath = os.path.join(summary_dir,file_desc)
    # summary_df = create_LCOH_results(str(result_dir),filepath)
    # summary_df.to_pickle(filepath + ".pkl")
    # summary_df.to_csv(filepath + ".csv")

    res_files = os.listdir(result_dir)
    result_type = "Summary"
    file_ext = ".pkl"

    summary_files = [f for f in res_files if result_type in f]
    summary_files = [f for f in summary_files if file_ext in f]

    main(summary_files,result_dir,filepath)
    # print("saved LCOH summary to: \n {}".format(filepath))

    # -------- IF LOCAL --------
    # result_dir = ROOT_DIR/"results"/"offgrid-baseline"/"equal-sized"/"ATB_2030"
    # summary_df = create_LCOH_results(str(result_dir))
    # summary_df.to_pickle(filepath + ".pkl")
    # summary_df.to_csv(filepath + ".csv")
    # print("saved LCOH summary to: \n {}".format(filepath))
    []