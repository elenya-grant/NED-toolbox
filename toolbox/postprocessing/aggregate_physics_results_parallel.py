import pandas as pd
import numpy as np
import os
from toolbox.utilities.file_tools import check_create_folder
from datetime import datetime
import sys
from mpi4py import MPI

def aggregate_files(filelist,results_dir,output_filename_base):
    site_keys = ["id","latitude","longitude","state"]
    index_keys = site_keys + ["RE Plant Design","H2 System Design"]
    summary_df = pd.DataFrame()
    
    for ii,file in enumerate(filelist):
        filepath = os.path.join(results_dir,file)
        df = pd.read_pickle(filepath)
        init_index_vals = df["Site"][site_keys].to_list()
        h2_design_descriptions = ["{} storage-{}".format(df["Physics"].iloc[i]["h2_storage_type"],df["Physics"].iloc[i]["h2_transport_type"]) for i in range(len(df["Physics"]))]
        
        unique_re_plant_types = list(np.unique(df["Physics"]["re_plant_type"]))
        unique_h2_design_types = list(np.unique(h2_design_descriptions))
        df["Physics"]["H2 System Design Scenario"] = h2_design_descriptions
        
        physics_df = df["Physics"]
        physics_df.index = [df["Physics"]["re_plant_type"],df["Physics"]["H2 System Design Scenario"]]
        physics_df = physics_df.drop(columns = ["h2_storage_type","h2_transport_type","re_plant_type","H2 System Design Scenario"])
        reformatted_physics_df = pd.DataFrame()
        for re_plant in unique_re_plant_types:
            for h2_design in unique_h2_design_types:
                physics_df.loc[re_plant].loc[h2_design]
                index = init_index_vals + [re_plant,h2_design]
                index = [[k] for k in index]
                physics_vals = list(physics_df.loc[re_plant].loc[h2_design]["renewables_summary"].values()) 
                columns = list(physics_df.loc[re_plant].loc[h2_design]["renewables_summary"].keys())
                
                h2_storage_types = list(physics_df.loc[re_plant].loc[h2_design]["h2_design_results"].keys())
                h2_storage_type = [k for k in h2_storage_types if "none" not in k]
                h2_storage_type = h2_storage_type[0]
        
                if any("h2_storage" in k for k in physics_df.loc[re_plant].loc[h2_design]["h2_design_results"][h2_storage_type].keys()):
                # if "h2_storage_results" in physics_df.loc[re_plant].loc[h2_design]:
                    h2_storage_cols = [k for k in list(physics_df.loc[re_plant].loc[h2_design]["h2_design_results"][h2_storage_type].keys()) if "h2_storage" in k]
                    h2_pipeline_cols = [k for k in list(physics_df.loc[re_plant].loc[h2_design]["h2_design_results"][h2_storage_type].keys()) if "h2_pipeline" in k]
                    h2_compressor_cols = [k for k in list(physics_df.loc[re_plant].loc[h2_design]["h2_design_results"][h2_storage_type].keys()) if "transport_compressor" in k]
                    h2_pipeline_cols = [k for k in h2_pipeline_cols if "[$]" not in k]
                    
                    h2_storage_vals = [physics_df.loc[re_plant].loc[h2_design]["h2_design_results"][h2_storage_type][k] for k in h2_storage_cols]
                    h2_pipeline_vals = [physics_df.loc[re_plant].loc[h2_design]["h2_design_results"][h2_storage_type][k] for k in h2_pipeline_cols]
                    h2_compressor_vals = [physics_df.loc[re_plant].loc[h2_design]["h2_design_results"][h2_storage_type][k] for k in h2_compressor_cols]

                    []
                    # h2_storage_vals = [physics_df.loc[re_plant].loc[h2_design]["h2_storage_results"][k] for k in h2_storage_cols]
                    physics_vals += h2_storage_vals
                    columns += h2_storage_cols

                    physics_vals +=h2_pipeline_vals
                    columns +=h2_pipeline_cols

                    physics_vals += h2_compressor_vals
                    columns += h2_compressor_cols
                
                h2_res_cols = [k for k in list(physics_df.loc[re_plant].loc[h2_design]["h2_results"].keys()) if "Rated BOL" not in k]
                h2_res_vals = [physics_df.loc[re_plant].loc[h2_design]["h2_results"][k] for k in h2_res_cols]
                physics_vals += h2_res_vals
                h2_res_cols = ["Electrolyzer: {}".format(k) for k in h2_res_cols]
                columns += h2_res_cols
                # lcoh_vals = physics_df.loc[re_plant].loc[h2_design]["lcoh"].to_list()
                # columns = physics_df.loc[re_plant].loc[h2_design]["Cost Scenario"].to_list()
                
                physics_temp = pd.DataFrame(dict(zip(columns,physics_vals)),index = [0])
                physics_temp.index = index
                reformatted_physics_df = pd.concat([physics_temp,reformatted_physics_df],axis=0)
        reformatted_physics_df.index = reformatted_physics_df.index.set_names(index_keys)
        summary_df = pd.concat([summary_df,reformatted_physics_df],axis=0)
    summary_df = summary_df.sort_index(axis=0,level="id",ascending=True)
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
    aggregate_files(s_list_chunks,result_dir,output_filepath_base_base + f"_{rank}")
    print(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")


if __name__ == "__main__":
    # from toolbox import ROOT_DIR, LIB_DIR
    # -------- IF KESTREL --------
    version = "v1"
    sweep_name = "offgrid-baseline"
    subsweep_name = "equal-sized"
    atb_year = 2030
    result_dir = "/projects/hopp/ned-results/{}/{}/{}/ATB_{}".format(version,sweep_name,subsweep_name,atb_year)
    summary_dir = "/projects/hopp/ned-results/{}/aggregated_results".format(version)
    check_create_folder(summary_dir)

    file_desc = "Physics_{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)
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