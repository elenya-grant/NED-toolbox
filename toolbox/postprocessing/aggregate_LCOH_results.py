import pandas as pd
import numpy as np
import os
from toolbox.utilities.file_tools import check_create_folder

def create_LCOH_results(results_dir:str):
    res_files = os.listdir(results_dir)
    result_type = "Summary"
    file_ext = ".pkl"

    summary_files = [f for f in res_files if result_type in f]
    summary_files = [f for f in summary_files if file_ext in f]
    site_keys = ["id","latitude","longitude","state"]
    index_keys = site_keys + ["RE Plant Design","H2 System Design"]
    summary_df = pd.DataFrame()
    for file in summary_files:
        filepath = os.path.join(results_dir,file)
        df = pd.read_pickle(filepath)
        # temp_df = pd.DataFrame(df["Site"][["id","latitude","longitude","state"]]).T
        init_index_vals = df["Site"][site_keys].to_list()

        cost_descriptions = ["LCOH [$/kg]: {}-{}-Policy#{}".format(df["LCOH"].iloc[i]["atb_year"],df["LCOH"].iloc[i]["atb_scenario"],df["LCOH"].iloc[i]["policy_scenario"]) for i in range(len(df["LCOH"]))]
        h2_design_descriptions = ["{} storage-{}".format(df["LCOH"].iloc[i]["h2_storage_type"],df["LCOH"].iloc[i]["h2_transport_design"]) for i in range(len(df["LCOH"]))]
        
        unique_re_plant_types = list(np.unique(df["LCOH"]["re_plant_type"]))
        unique_h2_design_types = list(np.unique(h2_design_descriptions))
        
        df["LCOH"]["Cost Scenario"] = cost_descriptions
        df["LCOH"]["H2 System Design Scenario"] = h2_design_descriptions
        
        lcoh_df = df["LCOH"].drop(columns = ["atb_year","atb_scenario","policy_scenario"])
        lcoh_df.index = [df["LCOH"]["re_plant_type"],df["LCOH"]["H2 System Design Scenario"]]
        lcoh_df = lcoh_df.drop(columns = ["h2_storage_type","h2_transport_design","re_plant_type","H2 System Design Scenario"])
        reformatted_lcoh_df = pd.DataFrame()
        for re_plant in unique_re_plant_types:
            for h2_design in unique_h2_design_types:
                lcoh_df.loc[re_plant].loc[h2_design]
                index = init_index_vals + [re_plant,h2_design]
                index = [[k] for k in index]
                lcoh_vals = lcoh_df.loc[re_plant].loc[h2_design]["lcoh"].to_list()
                columns = lcoh_df.loc[re_plant].loc[h2_design]["Cost Scenario"].to_list()
                lcoh_temp = pd.DataFrame(dict(zip(columns,lcoh_vals)),index = [0])
                lcoh_temp.index = index
                reformatted_lcoh_df = pd.concat([lcoh_temp,reformatted_lcoh_df],axis=0)
        reformatted_lcoh_df.index = reformatted_lcoh_df.index.set_names(index_keys)
        summary_df = pd.concat([summary_df,reformatted_lcoh_df],axis=0)
    return summary_df


if __name__ == "__main__":
    from toolbox import ROOT_DIR, LIB_DIR
    # -------- IF KESTREL --------
    version = 1
    sweep_name = "offgrid-baseline"
    subsweep_name = "equal-sized"
    atb_year = 2030
    result_dir = "/projects/hopp/ned-results/v{}/{}/{}/ATB_{}".format(version,sweep_name,subsweep_name,atb_year)
    summary_dir = "/projects/hopp/ned-results/v{}/aggregated_results".format(version)
    check_create_folder(summary_dir)

    file_desc = "LCOH_{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)
    filepath = os.path.join(summary_dir,file_desc)
    summary_df = create_LCOH_results(str(result_dir))
    summary_df.to_pickle(filepath + ".pkl")
    summary_df.to_csv(filepath + ".csv")
    print("saved LCOH summary to: \n {}".format(filepath))

    # -------- IF LOCAL --------
    # result_dir = ROOT_DIR/"results"/"offgrid-baseline"/"equal-sized"/"ATB_2030"
    # summary_df = create_LCOH_results(str(result_dir))
    # summary_df.to_pickle(filepath + ".pkl")
    # summary_df.to_csv(filepath + ".csv")
    # print("saved LCOH summary to: \n {}".format(filepath))
    []