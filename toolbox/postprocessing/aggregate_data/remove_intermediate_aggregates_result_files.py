import os
import pandas as pd

def remove_intermediate_results_files(aggregated_results_dir,keep_file_desc,remove_file_desc):
    all_files = os.listdir(aggregated_results_dir)
    remove_files = [f for f in all_files if keep_file_desc not in f]
    remove_files = [f for f in remove_files if remove_file_desc in f]

    for file in remove_files:
        delete_this_filepath = os.path.join(aggregated_results_dir,file)
        os.remove(delete_this_filepath)

    print("done deleting files")

def move_final_results_files(aggregated_results_dir,new_results_dir,move_file_desc,delete_moved_file=False):
    all_files = os.listdir(aggregated_results_dir)
    move_files = [f for f in all_files if move_file_desc in f]
    if not os.path.isdir(new_results_dir):
        os.makedirs(new_results_dir)

    for file in move_files:
        old_filepath = os.path.join(aggregated_results_dir,file)
        new_filepath = os.path.join(new_results_dir,file)
        copy_cmd = "cp {} {}".format(old_filepath,new_filepath)
        os.system(copy_cmd)
        if delete_moved_file:
            os.remove(old_filepath)
    
    print("done moving files to {}".format(new_results_dir))

if __name__ == "__main__":
    aggregated_results_dir = "/projects/hopp/ned-results/v1/aggregated_results"
    keep_file_desc = "Results--"
    # remove_file_desc = "Physics_offgrid-baseline_equal-sized_ATB_2030_"


    baseline_sweep = "offgrid-onshore"
    baseline_atb_year = 2030
    baseline_subsweeps = ["equal-sized","under-sized","over-sized"]
    baseline_result_types = ["LCOE","LCOH","Physics"]

    # ----- REMOVE INTERMEDIATE RESULTS FILES -----
    for result_type in baseline_result_types:
        for subsweep in baseline_subsweeps:
            baseline_remove_file_desc = "{}_{}_{}_ATB_{}_".format(result_type,baseline_sweep,subsweep,baseline_atb_year)
            remove_intermediate_results_files(aggregated_results_dir,keep_file_desc,baseline_remove_file_desc)
    
    new_baseline_results_agg_dir = os.path.join(aggregated_results_dir,baseline_sweep)

    for result_type in baseline_result_types:
        baseline_move_file_desc = "Results--{}_{}".format(result_type,baseline_sweep)
        move_final_results_files(aggregated_results_dir,new_baseline_results_agg_dir,baseline_move_file_desc,delete_moved_file=False)
    print("done cleaning up baseline results files")