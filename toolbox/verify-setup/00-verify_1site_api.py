from toolbox import LIB_DIR, INPUT_DIR
import pandas as pd
import yaml
from yamlinclude import YamlIncludeConstructor
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=LIB_DIR
)
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=LIB_DIR / "greenheart_hopp_config/"
)
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=LIB_DIR / "pv"
)
# from toolbox.utilities.file_tools import check_create_folder
from hopp.utilities import load_yaml
from toolbox.simulation.run_offgrid_onshore import setup_runs, run_baseline_site
import time
import os

start = time.perf_counter()
site_id = 4
atb_year = 2030
version_num = 1
sweep_name = "baseline-offgrid"
subsweep_name = "equal-sized"
input_filepath = INPUT_DIR/"v{}-{}/{}/main-{}.yaml".format(version_num,sweep_name,subsweep_name,atb_year)
input_config = load_yaml(input_filepath)

input_config["renewable_resource_origin"] = "API" #"API" or "HPC"
input_config.update({"env_path": "/scratch/egrant/NED/.env"}) 
input_config["hpc_or_local"] = "HPC"
# input_config["output_dir"] = "/kfs2/projects/hopp/ned-results/v1"
input_config["output_dir"] = os.path.join(os.path.dirname(__file__),"outputs","00")

site_list, inputs = setup_runs(input_config)

config_input_dict,ned_output_config_dict,ned_man = inputs
run_baseline_site(
    site_list.iloc[site_id].to_dict(),
    config_input_dict,
    ned_output_config_dict,
    ned_man,
    )

print("compeleted run")
end = time.perf_counter()
time_to_run = (end-start)/60
print("Took {} min to run 1 site using API".format(round(time_to_run,2)))