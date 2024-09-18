import pandas as pd
import numpy as np
import os
from toolbox.utilities.file_tools import check_create_folder

def create_LCOE_results(results_dir:str):
    res_files = os.listdir(results_dir)
    result_type = "Summary"
    file_ext = ".pkl"

    summary_files = [f for f in res_files if result_type in f]
    summary_files = [f for f in summary_files if file_ext in f]
    site_keys = ["id","latitude","longitude","state"]
    index_keys = site_keys + ["RE Plant Design"]
    summary_df = pd.DataFrame()
    for file in summary_files:
        filepath = os.path.join(results_dir,file)
        df = pd.read_pickle(filepath)
        # temp_df = pd.DataFrame(df["Site"][["id","latitude","longitude","state"]]).T
        init_index_vals = df["Site"][site_keys].to_list()

        cost_descriptions = ["LCOE [$/kWh]: {}-{}-Policy#{}".format(df["LCOE"].iloc[i]["atb_year"],df["LCOE"].iloc[i]["atb_scenario"],df["LCOE"].iloc[i]["policy_scenario"]) for i in range(len(df["LCOE"]))]
        # h2_design_descriptions = ["{} storage-{}".format(df["LCOE"].iloc[i]["h2_storage_type"],df["LCOE"].iloc[i]["h2_transport_design"]) for i in range(len(df["LCOE"]))]
        
        unique_re_plant_types = list(np.unique(df["LCOE"]["re_plant_type"]))
        # unique_h2_design_types = list(np.unique(h2_design_descriptions))
        
        df["LCOE"]["Cost Scenario"] = cost_descriptions
        # df["LCOE"]["H2 System Design Scenario"] = h2_design_descriptions
        
        lcoe_df = df["LCOE"].drop(columns = ["atb_year","atb_scenario","policy_scenario"])
        lcoe_df.index = [df["LCOE"]["re_plant_type"]]
        lcoe_df = lcoe_df.drop(columns = ["re_plant_type"])
        reformatted_lcoe_df = pd.DataFrame()
        for re_plant in unique_re_plant_types:
            lcoe_df.loc[re_plant]
            index = init_index_vals + [re_plant]
            index = [[k] for k in index]
            lcoe_vals = lcoe_df.loc[re_plant]["lcoe"].to_list()
            columns = lcoe_df.loc[re_plant]["Cost Scenario"].to_list()
            lcoe_temp = pd.DataFrame(dict(zip(columns,lcoe_vals)),index = [0])
            lcoe_temp.index = index
            reformatted_lcoe_df = pd.concat([lcoe_temp,reformatted_lcoe_df],axis=0)
        reformatted_lcoe_df.index = reformatted_lcoe_df.index.set_names(index_keys)
        summary_df = pd.concat([summary_df,reformatted_lcoe_df],axis=0)
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

    file_desc = "LCOE_{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)
    filepath = os.path.join(summary_dir,file_desc)
    summary_df = create_LCOE_results(str(result_dir))
    summary_df.to_pickle(filepath + ".pkl")
    summary_df.to_csv(filepath + ".csv")
    print("saved LCOE summary to: \n {}".format(filepath))

    # -------- IF LOCAL --------
    # result_dir = ROOT_DIR/"results"/"offgrid-baseline"/"equal-sized"/"ATB_2030"
    # summary_df = create_LCOE_results(str(result_dir))
    # summary_df.to_pickle(filepath + ".pkl")
    # summary_df.to_csv(filepath + ".csv")
    # print("saved LCOE summary to: \n {}".format(filepath))
    []