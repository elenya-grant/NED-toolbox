import os
import pandas as pd
import sys
def remove_intermediate_results_files(aggregated_results_dir,keep_file_desc,remove_file_desc):
    all_files = os.listdir(aggregated_results_dir)
    remove_files = [f for f in all_files if keep_file_desc not in f]
    remove_files = [f for f in remove_files if remove_file_desc in f]
    print("going to delete {} files".format(len(remove_files)))
    if len(remove_files)<50:
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
    
    
    if len(sys.argv)<3:
        electrolyzer_capex_version = "v1"
        atb_year = 2025
        finance_case = None
    else:
        electrolyzer_capex_version =  sys.argv[1]
        atb_year = int(sys.argv[2])
        if len(sys.argv)>3:
            finance_case = sys.argv[3]
        else:
            finance_case = None

    sweep_name = "offgrid-optimized"
    subsweep_name = "hybrid_renewables"
    result_type = "LCOH_Simplex"
    keep_file_desc = "Results--"

    electrolyzer_capex_versions = ["v1","v1_custom","v1_pathway"]
    if finance_case is None:
        run_desc = "{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)
    else:
        run_desc = "{}_{}_ATB_{}_{}".format(sweep_name,subsweep_name,atb_year,finance_case)
    
   
    summary_dir = "/projects/hopp/ned-results/{}/aggregated_results".format(electrolyzer_capex_version)
    
    # ----- REMOVE INTERMEDIATE RESULTS FILES FOR PARAMETRICSWEEP CASES -----
    # param_sweep_file_subdesc = ["FullParamSweep","OptimalParamSweep"]
    # param_sweep_result_types = ["LCOH_Simplex"] #["LCOE_Simplex","LCOH_Simplex","ParametricSweep_Results"]
    

    # for result_type in param_sweep_result_types:
    run_desc = "{}_{}_ATB_{}_{}".format(sweep_name,subsweep_name,atb_year,finance_case)
    summary_type = "FullParamSweep_{}".format(result_type)
    paramsweep_remove_file_desc = "{}_{}_".format(summary_type,run_desc)
    remove_intermediate_results_files(summary_dir,keep_file_desc,paramsweep_remove_file_desc)


    # ----- REMOVE AGGREGATED RESULT CSV FILES -----
    # keep_file_extension = ".pkl"
    # remove_file_extension = ".csv"
    # remove_intermediate_results_files(aggregated_results_dir,keep_file_extension,remove_file_extension)


    # new_baseline_results_agg_dir = os.path.join(aggregated_results_dir,baseline_sweep)

    # for result_type in baseline_result_types:
    #     baseline_move_file_desc = "Results--{}_{}".format(result_type,baseline_sweep)
    #     move_final_results_files(aggregated_results_dir,new_baseline_results_agg_dir,baseline_move_file_desc,delete_moved_file=False)
    print("done cleaning up baseline results files")