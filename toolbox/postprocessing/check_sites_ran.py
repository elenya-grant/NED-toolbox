import pandas as pd
import numpy as np
import os
from toolbox import ROOT_DIR,INPUT_DIR
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
    


if __name__ == "__main__":
    results_parent = "/projects/hopp/ned-results"
    version = "1"
    sweep_name = "offgrid-baseline"
    subsweep_name = "equal-sized"
    atb_year = 2030
    sim_desc = "v{}_{}_{}_{}".format(version,sweep_name,subsweep_name,atb_year)
    result_dir = os.path.join(results_parent,sweep_name,subsweep_name,"ATB_{}".format(atb_year))
    output_dir = os.path.join(str(ROOT_DIR),"sites_ran_info")
    check_create_folder(output_dir)
    check_folder_for_ran_sites(result_dir,output_dir,sim_desc)