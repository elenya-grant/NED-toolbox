from toolbox.simulation.ned_site import Site, NedManager
from toolbox import LIB_DIR, INPUT_DIR
import pandas as pd
import yaml
import os
import time
from yamlinclude import YamlIncludeConstructor
from pathlib import Path
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=LIB_DIR
)
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=LIB_DIR / "greenheart_hopp_config/"
)
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=LIB_DIR / "pv"
)
from toolbox.utilities.file_tools import check_create_folder
from hopp.utilities import load_yaml
import toolbox.simulation.greenheart_management as gh_mgmt
import toolbox.tools.interface_tools as int_tool
import copy
from toolbox.simulation.run_offgrid_onshore import setup_runs, run_baseline_site
from toolbox.simulation.results import NedOutputs

import sys
from mpi4py import MPI
from datetime import datetime



def do_something(site_list,inputs,site_id):
    config_input_dict,ned_output_config_dict,ned_man = inputs
    run_baseline_site(site_list.iloc[site_id].to_dict(),config_input_dict,ned_output_config_dict,ned_man)

start_time = datetime.now()

comm = MPI.COMM_WORLD
size = MPI.COMM_WORLD.Get_size()
rank = MPI.COMM_WORLD.Get_rank()
name = MPI.Get_processor_name()

def main(sitelist,inputs):
    """Main function
    Basic MPI job for embarrassingly paraller job:
    read data for multiple sites(gids) from one WTK .h5 file
    compute somthing (windspeed min, max, mean) for each site(gid)
    write results to .csv file for each site(gid)
    each rank will get about equal number of sites(gids) to process
    """

    ### output
    # output_dir = "/projects/hopp/ned/""
    # os.makedirs(output_dir, exist_ok=True)

    ### input
    # n_sites = 10
    # wtk_file = "/datasets/WIND/conus/v1.0.0/wtk_conus_2013.h5"

    ### site gids to process (e.g., could come form wtk file's meta)
    # site_idxs = pd.Index(range(n_sites))
    site_idxs = sitelist.index
    if rank == 0:
        print(" i'm rank {}:".format(rank))
        ################################ split site_idx's
        s_list = site_idxs.tolist()
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

        print(f"\n s_list_chunks {s_list_chunks}")
    else:
        s_list_chunks = None

    ### scatter
    s_list_chunks = comm.scatter(s_list_chunks, root=0)
    print(f"\n rank {rank} has sites {s_list_chunks} to process")

    # ### run sites in serial
    for i, gid in enumerate(s_list_chunks):
        # time.sleep(rank * 5)
        print(f"rank {rank} now processing its sites in serial: site gid {gid}")
        # file_out = os.path.join(output_dir, f"gid_{gid}_{rank}.csv")
        # variable = "windspeed_100m"
        # do_something(wtk_file, file_out, variable, gid)
        do_something(sitelist,inputs,gid)

    print(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")


if __name__ == "__main__":
    if len(sys.argv)<3:
        n_sites = 4 
        start_idx = 0
    else:
        n_sites = int(sys.argv[1])
        start_idx = int(sys.argv[2])

    input_filepath = INPUT_DIR/"v1-baseline-offgrid/equal-sized/main.yaml"
    input_config = load_yaml(input_filepath)
    
    site_list, inputs = setup_runs(input_config)
    sitelist = site_list.iloc[start_idx:start_idx+n_sites]

    main(sitelist,inputs)

