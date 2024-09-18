import pandas as pd
import numpy as np
import os
from toolbox.utilities.file_tools import check_create_folder

def create_physics_results(results_dir:str):
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

        # cost_descriptions = ["LCOH [$/kg]: {}-{}-Policy#{}".format(df["Physics"].iloc[i]["atb_year"],df["Physics"].iloc[i]["atb_scenario"],df["Physics"].iloc[i]["policy_scenario"]) for i in range(len(df["Physics"]))]
        h2_design_descriptions = ["{} storage-{}".format(df["Physics"].iloc[i]["h2_storage_type"],df["Physics"].iloc[i]["h2_transport_type"]) for i in range(len(df["Physics"]))]
        
        unique_re_plant_types = list(np.unique(df["Physics"]["re_plant_type"]))
        unique_h2_design_types = list(np.unique(h2_design_descriptions))
        
        # df["Physics"]["Cost Scenario"] = cost_descriptions
        df["Physics"]["H2 System Design Scenario"] = h2_design_descriptions
        
        physics_df = df["Physics"]
        physics_df.index = [df["Physics"]["re_plant_type"],df["Physics"]["H2 System Design Scenario"]]
        physics_df = physics_df.drop(columns = ["h2_storage_type","h2_transport_type","re_plant_type","H2 System Design Scenario"])
        reformatted_physics_df = pd.DataFrame()
        for re_plant in unique_re_plant_types:
            for h2_design in unique_h2_design_types:
                physics_df.loc[re_plant].loc[h2_design]
                index = init_index_vals + [re_plant,h2_design]
                index = [[k] for k in index]
                physics_vals = list(physics_df.loc[re_plant].loc[h2_design]["renewables_summary"].values()) 
                columns = list(physics_df.loc[re_plant].loc[h2_design]["renewables_summary"].keys())
                
                if "h2_storage_results" in physics_df.loc[re_plant].loc[h2_design]:
                    h2_storage_cols = [k for k in list(physics_df.loc[re_plant].loc[h2_design]["h2_storage_results"].keys()) if "h2" in k or "hydrogen" in k]
                    h2_storage_vals = [physics_df.loc[re_plant].loc[h2_design]["h2_storage_results"][k] for k in h2_storage_cols]
                    physics_vals += h2_storage_vals

                    h2_storage_cols = [k.replace("hydrogen","h2") for k in h2_storage_cols]
                    columns += h2_storage_cols
                    

                if "h2_transport_pipe_results" in physics_df.loc[re_plant].loc[h2_design]:
                    pipe_cols = [k for k in list(physics_df.loc[re_plant].loc[h2_design]["h2_transport_pipe_results"].keys()) if "[$]" not in k]
                    pipe_vals = [physics_df.loc[re_plant].loc[h2_design]["h2_transport_pipe_results"][k] for k in pipe_cols]
                    physics_vals += pipe_vals
                    pipe_cols = ["H2 Transport Pipe: {}".format(k) for k in pipe_cols]
                    columns +=pipe_cols
                if "h2_transport_compressor_results" in physics_df.loc[re_plant].loc[h2_design]:
                    comp_cols = [k for k in list(physics_df.loc[re_plant].loc[h2_design]["h2_transport_compressor_results"].keys()) if "opex" not in k or "capex" not in k]
                    comp_vals = [physics_df.loc[re_plant].loc[h2_design]["h2_transport_compressor_results"][k] for k in comp_cols]
                    physics_vals += comp_vals
                
                h2_res_cols = [k for k in list(physics_df.loc[re_plant].loc[h2_design]["h2_results"].keys()) if "Rated BOL" not in k]
                h2_res_vals = [physics_df.loc[re_plant].loc[h2_design]["h2_results"][k] for k in h2_res_cols]
                physics_vals += h2_res_vals
                h2_res_cols = ["Electrolyzer: {}".format(k) for k in h2_res_cols]
                columns += h2_res_cols
                # lcoh_vals = physics_df.loc[re_plant].loc[h2_design]["lcoh"].to_list()
                # columns = physics_df.loc[re_plant].loc[h2_design]["Cost Scenario"].to_list()
                
                physics_temp = pd.DataFrame(dict(zip(columns,physics_vals)),index = [0])
                physics_temp.index = index
                reformatted_physics_df = pd.concat([physics_temp,reformatted_physics_df],axis=0)
        reformatted_physics_df.index = reformatted_physics_df.index.set_names(index_keys)
        summary_df = pd.concat([summary_df,reformatted_physics_df],axis=0)
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

    file_desc = "Physics_{}_{}_ATB_{}".format(sweep_name,subsweep_name,atb_year)
    filepath = os.path.join(summary_dir,file_desc)
    summary_df = create_physics_results(str(result_dir))
    summary_df.to_pickle(filepath + ".pkl")
    summary_df.to_csv(filepath + ".csv")
    print("saved physics summary to: \n {}".format(filepath))

    # -------- IF LOCAL --------
    # result_dir = ROOT_DIR/"results"/"offgrid-baseline"/"equal-sized"/"ATB_2030"
    # summary_df = create_physics_results(str(result_dir))
    # summary_df.to_pickle(filepath + ".pkl")
    # summary_df.to_csv(filepath + ".csv")
    # print("saved physics summary to: \n {}".format(filepath))
    []