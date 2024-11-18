import pandas as pd
import os
from datetime import datetime
import sys
def combine_files(summary_dir,summary_type,run_desc):
    agg_files = os.listdir(summary_dir)
    agg_files = [f for f in agg_files if summary_type in f]
    agg_files = [f for f in agg_files if run_desc in f]
    agg_files = [f for f in agg_files if ".pkl" in f]
    agg_files = [f for f in agg_files if "Results--{}_{}".format(summary_type,run_desc) not in f]

    final_df = pd.DataFrame()
    print("start time: {}".format(datetime.now()))
    print("{} files to combine".format(len(agg_files)))
    for file in agg_files:
        filepath = os.path.join(summary_dir,file)
        df = pd.read_pickle(filepath)
        final_df = pd.concat([final_df,df],axis=0)
    
    output_filename_base = os.path.join(summary_dir,"Results--{}_{}".format(summary_type,run_desc))
    final_df.to_pickle(output_filename_base + ".pkl")
    # final_df.to_csv(output_filename_base + ".csv")
    print("final {} pickle filename is {}".format(summary_type,output_filename_base + ".pkl"))
    # print("final {} csv filename is {}".format(summary_type,output_filename_base + ".csv"))
    
if __name__ == "__main__":
    # from toolbox import ROOT_DIR, LIB_DIR
    # -------- IF KESTREL --------
    
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

    if finance_case is None:
        run_desc = "{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)
    else:
        run_desc = "{}_{}_ATB_{}_{}".format(sweep_name,subsweep_name,atb_year,finance_case)
    

    summary_dir = "/projects/hopp/ned-results/{}/aggregated_results".format(electrolyzer_capex_version)
    # summary_type = "FullParamSweep_{}".format(result_type) #["FullParamSweep_ParametricSweep_Results","FullParamSweep_LCOH_Simplex","FullParamSweep_LCOE_Simplex"] #
    summary_types = ["FullParamSweep_{}".format(result_type),"OptimalDesigns_ParamSweep_{}".format(result_type)]
    # electrolyzer_capex_versions = ["v1","v1_custom","v1_pathway"]
    for summary_type in summary_types:
        combine_files(summary_dir,summary_type,run_desc)