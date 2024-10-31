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
import toolbox.finance_reruns.rerun_baseline_for_new_costs as baseline_reruns
import sys
from mpi4py import MPI
from datetime import datetime
from toolbox import ROOT_DIR
from toolbox.utilities.ned_logger import mpi_logger as mpi_log
from toolbox.utilities.ned_logger import main_logger as main_log
import logging
import faulthandler
import numpy as np
faulthandler.enable()


def do_something(site_config,site_id):
    site_config = dict(site_config[site_id])
    
    previous_results_dir = os.path.join(site_config["previous_run_info"]["result_main_dir"],site_config["previous_run_info"]["sweep_name"],site_config["previous_run_info"]["subsweep_name"],"ATB_{}".format(site_config["previous_run_info"]["atb_year"]))
    
    if "sweep_name" in site_config["new_cost_info"]:
        new_results_dir = os.path.join(site_config["new_cost_info"]["output_dir_main"],site_config["new_cost_info"]["sweep_name"],site_config["previous_run_info"]["subsweep_name"],"ATB_{}".format(site_config["new_cost_info"]["new_atb_year"]))
    else:
        new_results_dir = os.path.join(site_config["new_cost_info"]["output_dir_main"],site_config["previous_run_info"]["sweep_name"],site_config["previous_run_info"]["subsweep_name"],"ATB_{}".format(site_config["new_cost_info"]["new_atb_year"]))
    if site_config["new_cost_info"]["weighted_finances"]:
        new_results_dir = os.path.join(new_results_dir,"weighted_financials")

    if not os.path.isdir(new_results_dir):
        os.makedirs(new_results_dir,exist_ok=True)
    
    result_files = os.listdir(previous_results_dir)
    site_files = [f for f in result_files if f.split("-")[0]==str(site_id)]
    if len(site_files)>0:
        site_file_desc = site_files[0].split("-{}-".format(site_config["previous_run_info"]["atb_year"]))[0]
        site_file_desc += "--LCOH_Detailed.pkl"
        output_filename = os.path.join(new_results_dir,site_file_desc)
        lcoh_filenames = [f for f in site_files if "LCOH_Detailed.pkl" in f]
        summary_filenames = [f for f in site_files if "--Summary.pkl" in f]
        lcoh_res,physics_res = baseline_reruns.combine_lcoh_physics_results(previous_results_dir,lcoh_filenames,summary_filenames)
        finance_dir = os.path.join(str(LIB_DIR),"finance")
        gh_hopp_dir = os.path.join(str(LIB_DIR),"greenheart_hopp_config")
        greenheart_filepath = os.path.join(gh_hopp_dir,site_config["new_cost_info"]["greenheart_config_filename"])
        hopp_cost_filepath = os.path.join(finance_dir,site_config["new_cost_info"]["hopp_cost_filename"])
        electrolyzer_cost_filepath = os.path.join(finance_dir,site_config["new_cost_info"]["atb_cost_filename"])
        profast_config_filepath = os.path.join(finance_dir,site_config["new_cost_info"]["profast_filename"])
        if site_config["new_cost_info"]["weighted_finances"]:
            weighted_financials_filename = os.path.join(finance_dir,site_config["new_cost_info"]["weighted_finances_filename"])
            weighted_financials_config = load_yaml(weighted_financials_filename)
        else:
            weighted_financials_config = None
        new_greenheart_config = load_yaml(greenheart_filepath)
        new_hopp_costs = load_yaml(hopp_cost_filepath)
        new_electrolyzer_costs = load_yaml(electrolyzer_cost_filepath)
        profast_config = load_yaml(profast_config_filepath)
        new_greenheart_config["finance_parameters"].update({"profast_config":profast_config})
        new_greenheart_config["project_parameters"].update({"atb_year":site_config["new_cost_info"]["new_atb_year"]})
        baseline_reruns.run_new_costs_for_lcoh_baseline_cases(
            lcoh_res,
            physics_res,
            output_filename,
            site_config["new_cost_info"]["new_atb_year"],
            copy.deepcopy(new_greenheart_config),
            new_electrolyzer_costs,
            new_hopp_costs,
            save_pf_config = site_config["new_cost_info"]["save_pf_config"],
            weight_vre_h2_params = site_config["new_cost_info"]["weighted_finances"], 
            vre_h2_finance_assumptions = weighted_financials_config)
    else:
        main_log.warning("Site {} does not have site files".format(site_id))

start_time = datetime.now()

comm = MPI.COMM_WORLD
size = MPI.COMM_WORLD.Get_size()
rank = MPI.COMM_WORLD.Get_rank()
name = MPI.Get_processor_name()

def main(site_ids,input_config,verbose = False):
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
    ### site gids to process (e.g., could come form wtk file's meta)
    
    
    if rank == 0:
        print(" i'm rank {}:".format(rank))
        ################################ split site_idx's
        s_list = list(site_ids)
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
        site_config = {}
        site_config.update({gid:copy.deepcopy(input_config)})
        do_something(site_config,gid)
    if verbose:
        print(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")
    mpi_log.info(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")


if __name__ == "__main__":
    if len(sys.argv)<3:
        subsweep_name = "equal-sized"
        rerun_input_filename = "rerun_ATB2024_weighted.yaml"
    else:
        subsweep_name = sys.argv[1]
        rerun_input_filename = sys.argv[2]

    
    
    input_filepath = INPUT_DIR/"v1-baseline-offgrid-reruns"/rerun_input_filename
    rerun_config = load_yaml(input_filepath)
    rerun_config["previous_run_info"].update({"subsweep_name":subsweep_name})
    site_ids = np.arange(0,50082,1)
    # below is to run on HPC
    # input_config.update({"renewable_resource_origin":"HPC"}) #"API" or "HPC"
    # input_config.update({"hpc_or_local":"HPC"})
    # input_config.update({"output_dir":"/projects/hopp/ned-results/v1"})
    
    # below is to run locally
    # input_config["renewable_resource_origin"] = "API" #"API" or "HPC"
    # input_config["hpc_or_local"] = "local"
    # if "env_path" in input_config:
    #     input_config.pop("env_path")
    # input_config.pop("output_dir")
    
    
    main_log.info("set up runs")
    
    main(site_ids,rerun_config)

