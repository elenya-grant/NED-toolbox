# from toolbox.simulation.ned_site import Site, NedManager
from toolbox import LIB_DIR, INPUT_DIR
import pandas as pd
import yaml
import os
import time
import logging
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
# from toolbox.utilities.file_tools import check_create_folder
from hopp.utilities import load_yaml
# import toolbox.simulation.greenheart_management as gh_mgmt
# import toolbox.tools.interface_tools as int_tool
import copy
import toolbox.simulation.plant.design.optimization_tools as opt_tools
# from toolbox.simulation.results import NedOutputs
from toolbox.simulation.plant.design.run_optimization_simulations import run_site_optimization
import sys
from mpi4py import MPI
from datetime import datetime
from toolbox import ROOT_DIR
from toolbox.utilities.ned_logger import mpi_logger as mpi_log
from toolbox.utilities.ned_logger import main_logger as main_log
import logging
import faulthandler
faulthandler.enable()


def do_something(site_list,inputs,site_id):
    mpi_log.info("Site {}: starting".format(site_id))
    ned_manager_dict,config_input_dict,ned_output_config_dict,sitelist_simplex,optimize_designs = inputs
    if sitelist_simplex is not None:
        site_simplex = sitelist_simplex.loc[site_id]
    else:
        site_simplex = None
    run_site_optimization(site_list.loc[site_id].to_dict(),site_simplex,ned_manager_dict,config_input_dict,ned_output_config_dict,optimization_config,run_full_optimization = optimize_designs)
    mpi_log.info("Site {}: complete".format(site_id))

start_time = datetime.now()

comm = MPI.COMM_WORLD
size = MPI.COMM_WORLD.Get_size()
rank = MPI.COMM_WORLD.Get_rank()
name = MPI.Get_processor_name()

def main(sitelist,inputs,verbose = False):
    """Main function
    Basic MPI job for embarrassingly paraller job:
    read data for multiple sites(gids) from one WTK .h5 file
    compute somthing (windspeed min, max, mean) for each site(gid)
    write results to .csv file for each site(gid)
    each rank will get about equal number of sites(gids) to process
    """

    ### input
    main_log.info(f"START TIME: {start_time}")
    main_log.info("number of ranks: {}".format(size))
    main_log.info("number of sites: {}".format(len(sitelist)))
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
        if verbose:
            print(f"\n s_list_chunks {s_list_chunks}")
        main_log.info(f"s_list_chunks {s_list_chunks}")
    else:
        s_list_chunks = None

    ### scatter
    s_list_chunks = comm.scatter(s_list_chunks, root=0)
    if verbose:
        print(f"\n rank {rank} has sites {s_list_chunks} to process")
    main_log.info(f"rank {rank} has sites {s_list_chunks} to process")

    # ### run sites in serial
    for i, gid in enumerate(s_list_chunks):
        # time.sleep(rank * 5)
        if verbose:
            print(f"rank {rank} now processing its sites in serial: site gid {gid}")
        mpi_log.info(f"rank {rank} now processing its sites in serial: Site {gid}")
        inputs_copied = [copy.deepcopy(inpt) for inpt in inputs]
        do_something(sitelist,inputs_copied,gid)
    if verbose:
        print(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")
    mpi_log.info(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")


if __name__ == "__main__":
    if len(sys.argv)<3:
        n_sites = 4 
        start_idx = 0
    else:
        n_sites = int(sys.argv[1])
        start_idx = int(sys.argv[2])

    
    atb_year = 2025
    optimize_designs = False
    input_filepath = INPUT_DIR/"v1-optimize-offgrid/main-{}.yaml".format(atb_year)
    optimization_filepath = INPUT_DIR/"v1-optimize-offgrid/optimize_config_{}.yaml".format(atb_year)
    input_config = load_yaml(input_filepath)
    optimization_config = load_yaml(optimization_filepath)

    
    # below is to run on HPC
    # input_config["renewable_resource_origin"] = "HPC" #"API" or "HPC"
    # input_config["hpc_or_local"] = "HPC"
    # input_config["output_dir"] = "/projects/hopp/ned-results/v1"
    # previous_run_dir_hpc = "/projects/hopp/ned-results/v1"
    # optimization_config["existing_timeseries_info"].update({"prev_run_main_output_dir":previous_run_dir_hpc})
    
    # below is to run locally
    input_config["renewable_resource_origin"] = "API" #"API" or "HPC"
    input_config["hpc_or_local"] = "local"
    if "env_path" in input_config:
        input_config.pop("env_path")
    input_config.pop("output_dir")
    previous_run_dir_local = os.path.join(str(ROOT_DIR),"results")
    optimization_config["existing_timeseries_info"].update({"prev_run_main_output_dir":previous_run_dir_local})
    
    #get inputs
    ned_manager_dict,config_input_dict,ned_output_config_dict,site_list,sitelist_simplex = opt_tools.initialize_optimization_data(input_config,optimization_config)
    
    inputs = [ned_manager_dict,config_input_dict,ned_output_config_dict,sitelist_simplex,optimize_designs]
    main_log.info("set up runs")
    end_idx = start_idx + n_sites
    if end_idx>=len(site_list):
        sitelist = site_list.iloc[start_idx:]
    else:
        sitelist = site_list.iloc[start_idx:start_idx+n_sites]
    
    main(sitelist,inputs)

