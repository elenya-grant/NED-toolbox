import os
from toolbox.utilities.file_tools import load_dill_pickle,dump_data_to_pickle
import pandas as pd

def combine_files(dir,file_names,output_filename):
    data = pd.DataFrame()
    n_files = len(file_names)
    for file in file_names:
        chunk = load_dill_pickle(os.path.join(dir,file))
        data = pd.concat([data,chunk],axis=0)
    
    data = data.sort_index(level="id")
    output_filepath = os.path.join(dir,output_filename)
    dump_data_to_pickle(data,output_filepath)
    print(f"done combining {n_files} files")
    print(f"saved file to {output_filepath}")


if __name__=="__main__":
    res_type = "lcoe" #"lcoe" or "lcoh"
    output_results_dir = "/projects/hopp/ned-results/iedo_electrowinning_results/"
    file_desc = f"2025_min_{res_type}_chunks_"
    the_final_filename = f"minimum_{res_type}_results_2025_Moderate.pkl"
    res_files = os.listdir(output_results_dir)
    res_files = [f for f in res_files if ".pkl" in f]

    the_files = [f for f in res_files if file_desc in f]
    combine_files(output_results_dir,the_files,the_final_filename)
    