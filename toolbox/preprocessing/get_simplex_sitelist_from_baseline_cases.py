import pandas as pd
import os
import numpy as np
from toolbox.tools.environment_tools import set_local_results_dir_dot_env
from toolbox.tools.environment_tools import get_local_results_dir
from toolbox import SITELIST_DIR

def remove_duplicate_design_entries(d_data):
    i_locs_all = np.arange(0,len(d_data),1)
    i_locs_drop = i_locs_all[1::2]
    d_data["i"] = i_locs_all
    d_data = d_data.set_index("i",append=True)
    d_data = d_data.drop(labels=i_locs_drop,axis=0,level="i")
    
    return d_data.droplevel("i")



set_local_results_dir_dot_env()
results_dir = get_local_results_dir()
sweep_name = "offgrid-baseline"
subsweep_names = ["equal-sized","under-sized","over-sized"]
atb_year = 2030
version = 1


simplex_h2_storage_type = "pipe" #pipe or none if on-site, salt_cavern or lined_rock_cavern if geologic
simplex_h2_storage_desc = "on-site" #"on-site" or "geologic"
simplex_h2_transport_desc = "colocated" #"colocated" or "pipeline"
simplex_h2_system_design = "pipe storage-colocated"
simplex_h2_system_design_design = "pipe storage-colocated"
simplex_atb_scenario = "Moderate"
simplex_policy_scenario = "1"
simplex_design_variables = ["PV: System Capacity [kW-DC]","Wind: System Capacity [kW]","Battery: System Capacity [kW]","Battery: System Capacity [kWh]"]
results_path = os.path.join(results_dir, "v{}".format(version))
lcoh_column_name = "LCOH [$/kg]: {}-{}-Policy#{}".format(atb_year,simplex_atb_scenario,simplex_policy_scenario)

simplex_df = pd.DataFrame()
for i in range(len(subsweep_names)):
    lcoh_data_filepath = os.path.join(results_path,"Results--LCOH_{}_{}_ATB_{}.pkl".format(sweep_name,subsweep_names[i],atb_year))
    physics_data_filepath = os.path.join(results_path,"Results--Physics_{}_{}_ATB_{}.pkl".format(sweep_name,subsweep_names[i],atb_year))
    lcoh_data = pd.read_pickle(lcoh_data_filepath)
    design_data = pd.read_pickle(physics_data_filepath)
    design_data = design_data.sort_index(axis = 0,level="id")
    lcoh_data = lcoh_data.sort_index(axis = 0,level="id")
    
    lcoh_data = lcoh_data.reorder_levels(["H2 System Design","RE Plant Design","id","latitude","longitude","state"]) #lcoh_data.swaplevel("id","H2 System Design").swaplevel("latitude","RE Plant Design").swaplevel("longitude","id")
    lcoh_data = lcoh_data.loc["{} storage-{}".format(simplex_h2_storage_type,simplex_h2_transport_desc)][lcoh_column_name]
    design_data = design_data.reorder_levels(["H2 System Design","RE Plant Design","id","latitude","longitude","state"]) #.swaplevel("id","H2 System Design").swaplevel("latitude","RE Plant Design").swaplevel("longitude","id")
    design_data = design_data.loc["{} storage-{}".format(simplex_h2_storage_desc,simplex_h2_transport_desc)][simplex_design_variables].fillna(value=0)
    if len(design_data) != len(lcoh_data):
        design_data = remove_duplicate_design_entries(design_data)

    temp_simplex_df = pd.concat([design_data,lcoh_data],axis=1)
    
    temp_simplex_df["Case"] = [subsweep_names[i]]*len(temp_simplex_df)
    temp_simplex_df = temp_simplex_df.set_index("Case",append=True)
    simplex_df = pd.concat([simplex_df,temp_simplex_df],axis=0)
    []
simplex_df = simplex_df.reorder_levels(["id","latitude","longitude","state","Case","RE Plant Design"])
simplex_filename = "OffGridBaseline_SimplexSiteList_{}-{}-{}_{}-{}-{}".format(simplex_atb_scenario,atb_year,simplex_policy_scenario,simplex_h2_storage_desc,simplex_h2_storage_type,simplex_h2_transport_desc)
simplex_filepath = os.path.join(str(SITELIST_DIR),simplex_filename)
simplex_df.to_csv(simplex_filepath + ".csv")
simplex_df.to_pickle(simplex_filepath + ".pkl")
print("Saved Simplex data as {}".format(simplex_filename))
[]