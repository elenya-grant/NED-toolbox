import pandas as pd
import numpy as np
import os
import faulthandler
faulthandler.enable()
from toolbox import ROOT_DIR,INPUT_DIR,SITELIST_DIR
from toolbox.utilities.file_tools import check_create_folder
import datetime
def check_folder_for_ran_sites(result_dir,output_dir,sim_desc):
    todays_date = datetime.datetime.now().strftime("%x").replace("/","-")
    res_files = os.listdir(result_dir)
    print("{} result files".format(len(res_files)))

    site_gids = [int(f.split("-")[0]) for f in res_files if "ned_man" not in f]
    site_ids, site_id_cnt = np.unique(site_gids,return_counts=True)
    n_sites = len(site_ids)
    file_desc = "sites_ran_{}--{}.csv".format(sim_desc,todays_date)
    output_filename = os.path.join(output_dir,file_desc)
    
    print("{} sites ran".format(n_sites))
    df = pd.DataFrame({"site ids":site_ids,"# files":site_id_cnt})
    df.to_csv(output_filename)
    print("output filepath \n")
    print(output_filename)
    

def make_list_of_remaining_sites(result_dir,output_dir,sim_desc):
    n_files_successful = 10
    sitelist_filepath = os.path.join(str(SITELIST_DIR),"ned_final_sitelist_50082locs.csv")
    site_list = pd.read_csv(sitelist_filepath,index_col = "Unnamed: 0")
    sites_ran = check_folder_for_ran_sites(result_dir,output_dir,sim_desc)
    sites_ran.index = sites_ran["site ids"].to_list()
    site_list.index = site_list["id"].to_list()

    site_id_todo = []
    sites_partial = sites_ran[sites_ran["# files"] != n_files_successful]
    site_id_todo += sites_partial["site ids"].to_list()
    
    site_id_todo += [i for i in site_list.index.to_list() if i not in sites_ran.index.to_list()]
    site_id_todo = list(np.unique(site_id_todo))
    sites_remaining = site_list.loc[site_id_todo]

    sitelist_filename_todo = os.path.join(str(SITELIST_DIR),"ned_sitelist_{}locs.csv".format(len(sites_remaining)))
    print("New sitelist filepath: \n {}".format(sitelist_filename_todo))
    sites_remaining.to_csv(sitelist_filename_todo)
    print("saved csv")

if __name__ == "__main__":
    results_parent = "/projects/hopp/ned-results"
    version = "1"
    sweep_name = "offgrid-baseline"
    subsweep_name = "over-sized" #"equal-sized"
    atb_year = 2030
    sim_desc = "v{}_{}_{}_{}".format(version,sweep_name,subsweep_name,atb_year)
    result_dir = os.path.join(results_parent,"v{}".format(version),sweep_name,subsweep_name,"ATB_{}".format(atb_year))
    output_dir = os.path.join(str(ROOT_DIR),"sites_ran_info")
    check_create_folder(output_dir)

    make_list_of_remaining_sites(result_dir,output_dir,sim_desc)
    # os.path.getsize("/projects/hopp/")
    # check_folder_for_ran_sites(result_dir,output_dir,sim_desc)