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
    index_keys = site_keys + ["RE Plant Design","H2 System Design"]
    for ii,file in enumerate(filelist):
        filepath = os.path.join(results_dir,file)
        df = pd.read_pickle(filepath)
        init_index_vals = df["Site"][site_keys].to_list()

        cost_descriptions = ["LCOH [$/kg]: {}-{}-Policy#{}".format(df["LCOH"].iloc[i]["atb_year"],df["LCOH"].iloc[i]["atb_scenario"],df["LCOH"].iloc[i]["policy_scenario"]) for i in range(len(df["LCOH"]))]
        h2_design_descriptions = ["{} storage-{}".format(df["LCOH"].iloc[i]["h2_storage_type"],df["LCOH"].iloc[i]["h2_transport_design"]) for i in range(len(df["LCOH"]))]
        
        unique_re_plant_types = list(np.unique(df["LCOH"]["re_plant_type"]))
        unique_h2_design_types = list(np.unique(h2_design_descriptions))
        
        df["LCOH"]["Cost Scenario"] = cost_descriptions
        df["LCOH"]["H2 System Design Scenario"] = h2_design_descriptions
        
        lcoh_df = df["LCOH"].drop(columns = ["atb_year","atb_scenario","policy_scenario"])
        lcoh_df.index = [df["LCOH"]["re_plant_type"],df["LCOH"]["H2 System Design Scenario"]]
        lcoh_df = lcoh_df.drop(columns = ["h2_storage_type","h2_transport_design","re_plant_type","H2 System Design Scenario"])
        reformatted_lcoh_df = pd.DataFrame()
        for re_plant in unique_re_plant_types:
            for h2_design in unique_h2_design_types:
                lcoh_df.loc[re_plant].loc[h2_design]
                index = init_index_vals + [re_plant,h2_design]
                index = [[k] for k in index]
                lcoh_vals = lcoh_df.loc[re_plant].loc[h2_design]["lcoh"].to_list()
                columns = lcoh_df.loc[re_plant].loc[h2_design]["Cost Scenario"].to_list()
                lcoh_temp = pd.DataFrame(dict(zip(columns,lcoh_vals)),index = [0])
                lcoh_temp.index = index
                reformatted_lcoh_df = pd.concat([lcoh_temp,reformatted_lcoh_df],axis=0)
        reformatted_lcoh_df.index = reformatted_lcoh_df.index.set_names(index_keys)
        summary_df = pd.concat([summary_df,reformatted_lcoh_df],axis=0)
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

    file_desc = "LCOH_{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)
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