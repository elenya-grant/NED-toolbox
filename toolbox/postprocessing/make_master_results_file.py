import pandas as pd
import os
def combine_files(summary_dir,summary_type,run_desc):
    agg_files = os.listdir(summary_dir)
    agg_files = [f for f in agg_files if summary_type in f]
    agg_files = [f for f in agg_files if run_desc in f]
    agg_files = [f for f in agg_files if ".pkl" in f]

    final_df = pd.DataFrame()
    for file in agg_files:
        filepath = os.path.join(summary_dir,file)
        df = pd.read_pickle(filepath)
        final_df = pd.concat([final_df,df],axis=0)
    
    output_filename_base = os.path.join(summary_dir,"Results--{}_{}".format(summary_type,run_desc))
    final_df.to_pickle(output_filename_base + ".pkl")
    final_df.to_csv(output_filename_base + ".csv")
    print("final {} pickle filename is {}".format(summary_type,output_filename_base + ".pkl"))
    print("final {} csv filename is {}".format(summary_type,output_filename_base + ".csv"))
    
if __name__ == "__main__":
    # from toolbox import ROOT_DIR, LIB_DIR
    # -------- IF KESTREL --------
    version = 1
    sweep_name = "offgrid-baseline"
    subsweep_name = "equal-sized"
    atb_year = 2030
    summary_dir = "/projects/hopp/ned-results/v{}/aggregated_results".format(version)

    summary_type = "LCOH" #"LCOH" "LCOE" "Physics"
    run_desc = "{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)
    
    # file_desc = "Physics_{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)