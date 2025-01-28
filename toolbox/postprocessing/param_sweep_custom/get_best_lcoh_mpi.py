from toolbox import SITELIST_DIR
import toolbox.postprocessing.param_sweep_custom.lcoh_sweep_tools as lcoh_tools
import pandas as pd
import os
from toolbox.utilities.file_tools import check_create_folder
from datetime import datetime
import sys
from mpi4py import MPI
from toolbox.utilities.file_tools import dump_data_to_pickle

save_pf_config = False
def run_lcoh_chunk_of_sites(sitelist,sites_to_run,input_results_dir,output_filepath):
    res = pd.DataFrame()
    for site_id in sites_to_run:
        site_res = lcoh_tools.run_min_lcoh_for_site(input_results_dir,site_id,state = sitelist.loc[site_id]["state"],lat = sitelist.loc[site_id]["latitude"],lon=sitelist.loc["longitude"])
        res = pd.concat([res,site_res],axis=0)
    if not save_pf_config:
        res = res.drop(columns=["lcoh_pf_config"])
    dump_data_to_pickle(res,output_filepath)
start_time = datetime.now()

comm = MPI.COMM_WORLD
size = MPI.COMM_WORLD.Get_size()
rank = MPI.COMM_WORLD.Get_rank()
name = MPI.Get_processor_name()

def main(sitelist,result_dir,output_filepath_base_base):
    if rank == 0:
        print(" i'm rank {}:".format(rank))
        ################################ split site_idx's
        s_list = sitelist.index.to_list()
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
    print(f"\n rank {rank} has its files to process")
    run_lcoh_chunk_of_sites(sitelist,s_list_chunks,result_dir,output_filepath_base_base + f"_{rank}.pkl")
    print(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")

if __name__ == "__main__":
    hpc_res_dir = "/projects/hopp/ned-results/v1/offgrid-optimized/hybrid_renewables/ATB_2025"
    output_results_dir = "/projects/hopp/ned-results/iedo_electrowinning_results/"
    sitelist_fpath = SITELIST_DIR/"ned_final_sitelist_50082locs.csv"
    sitelist_df = pd.read_csv(sitelist_fpath,index_col = "id")

    check_create_folder(output_results_dir)
    output_filepath_base_desc = os.path.join(output_results_dir,"2025_min_lcoh_chunks")
    main(sitelist_df,hpc_res_dir,output_filepath_base_desc)
    