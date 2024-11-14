from toolbox import LIB_DIR
from toolbox import INPUT_DIR,ROOT_DIR
import os
import pandas as pd
from toolbox.utilities.yaml_tools import load_yaml
from attrs import define, field
from toolbox.utilities.file_tools import check_create_folder
from toolbox.simulation.ned_base import BaseClassNed
import shutil

run_notes_dir = os.path.join(str(ROOT_DIR),"docs","more_reruns")
if not os.path.isdir(run_notes_dir):
    os.makedirs(run_notes_dir,exist_ok=True)
input_config_dir = os.path.join(str(INPUT_DIR),"v1-rerun-paramsweep")
template_config_filepath = os.path.join(input_config_dir,"rerun_template.yaml")

finance_dir = os.path.join(str(LIB_DIR),"finance")
# finance parameter cases:
finance_case_info_filepath = os.path.join(finance_dir,"FinanceReRun_Summary.yaml")
finance_case_summary = load_yaml(finance_case_info_filepath)

cost_years = [2022,2024,2025,2026,2030]
elec_cost_version_and_desc = {"v1":"baseline","v1_custom":"expensive","v1_pathway":"cheap"}
baseline_elec_cost_files = ["GreenSteel_ElectrolyzerCosts_2022USD_2022.yaml",
    "GreenSteel_ElectrolyzerCosts_2022USD_2024.yaml",
    "ATB2024_technology_cost_cases_2022USD_2025.yaml",
    "GreenSteel_ElectrolyzerCosts_2022USD_2026.yaml",
    "ATB2024_technology_cost_cases_2022USD_2030.yaml"]
expensive_elec_cost_file = ["TechnologyCostCases_2022USD_HFTO.yaml"]*len(cost_years)
cheap_elec_cost_file = ["LowElectrolyzerCapex_Cases.yaml"]*len(cost_years)
elec_capex_cases_config = {"v1":dict(zip(cost_years,baseline_elec_cost_files)),
"v1_custom":dict(zip(cost_years,expensive_elec_cost_file)),
"v1_pathway":dict(zip(cost_years,cheap_elec_cost_file))}

config_filename_tracker = []
# input_config_dir = os.path.join(str(INPUT_DIR),"v1-parametricsweep-offgrid-reruns")
for cost_version,elec_capex_years_files in elec_capex_cases_config.items():
    for atb_year,elec_cost_file in elec_capex_years_files.items():
        for finance_num,profast_filename in finance_case_summary.items():
            finance_case_desc = profast_filename.split("profast_config_v1_")[-1]
            finance_case_desc = finance_case_desc.split(".yaml")[0]

            new_config_filename = "rerun_{}_{}_{}.yaml".format(cost_version,atb_year,finance_case_desc)
            new_config_filepath = os.path.join(input_config_dir,new_config_filename)
            shutil.copy(template_config_filepath,new_config_filepath)
            #read in new file
            with open(new_config_filepath,"r") as f:
                file_contents = f.read()
            file_contents = file_contents.replace("<atb_year>",str(atb_year))
            file_contents = file_contents.replace("<output_dir_desc>",cost_version)
            file_contents = file_contents.replace('<electrolyzer_cost_case_filename>','"{}"'.format(elec_cost_file))
            file_contents = file_contents.replace('<finance_case_filename>','"{}"'.format(profast_filename))
            with open(new_config_filepath, 'w') as f:
                f.write(file_contents)
            
            config_filename_tracker.append(new_config_filename)

config_filename_tracker_lines = ["Input Path: {}".format(input_config_dir)]
config_filename_tracker_lines += ["\t- [ ] {}".format(f) for f in config_filename_tracker]
config_files_list_contents = "\n".join(k for k in config_filename_tracker_lines)
config_notes_list_filepath = os.path.join(run_notes_dir,"finance_reruns_input_filenames-paramsweep.md")
with open(config_notes_list_filepath,"w") as f:
    f.write(config_files_list_contents)  
                    
# input_config_dir = os.path.join(str(INPUT_DIR),"v1-baseline-offgrid-reruns")