from toolbox import INPUT_DIR
from hopp.utilities import load_yaml
import os
from toolbox import INPUT_DIR
import shutil
from toolbox.utilities.file_tools import check_create_folder

batch_number = "01"

input_config_dir = os.path.join(str(INPUT_DIR),"v1-postprocess")
input_info_file = os.path.join(input_config_dir,"batch_{}.yaml".format(batch_number))
input_info = load_yaml(input_info_file)


template_names = ["postprocess_finrerun_01_paramsweep_template.sh","postprocess_finrerun_01b_paramsweep_template.sh"]
job_keys = ["fullparam_job_desc","optimalparam_job_desc"]
batch_subdirs = ["finrerun_01","finrerun_01b"]

for ii in range(len(template_names)):
    
    example_batch_script_filepath = os.path.join(str(INPUT_DIR),"batch-scripts",template_names[ii])
    batch_script_dir = os.path.join(str(INPUT_DIR),"batch-scripts",batch_subdirs[ii])
    check_create_folder(batch_script_dir)

    batch_script_filename_list = []
    job_name_list = []
    case_tracker = []
    for fin_case in input_info["finance_cases"]:
        for atb_year in input_info["atb_years"]:
            for capex_version in input_info["electrolyzer_cost_cases"]:
                res_dir = "/projects/hopp/ned-results/{}/{}/{}/ATB_{}/{}".format(capex_version,input_info["sweep"],input_info["subsweep"],atb_year,fin_case)
                if os.path.isdir(res_dir):
                    filename = "fin_rerun_{}_{}_{}".format(capex_version,atb_year,fin_case)
                    new_batch_script_filename = os.path.join(batch_script_dir,filename + ".sh")
                    batch_script_filename_list.append(new_batch_script_filename)
                    #copy template contents to new script
                    shutil.copy(example_batch_script_filepath,new_batch_script_filename)
                    with open(new_batch_script_filename,"r") as f:
                        file_contents = f.read()
                    new_jobname = "rerun-{}".format(filename)
                    file_contents = file_contents.replace(job_keys[ii],new_jobname)
                    file_contents = file_contents.replace("e_capex_version",capex_version)
                    file_contents = file_contents.replace("atb_year",atb_year)
                    file_contents = file_contents.replace("fin_case",fin_case)
                    job_name_list.append(new_jobname)
                    case_tracker.append(filename)
                    with open(new_batch_script_filename, 'w') as f:
                        f.write(file_contents)

    batch_case_list_filepaths = ["NED-toolbox/{}".format(k.split("NED-toolbox/")[-1]) for k in batch_script_filename_list]
    batch_case_list_lines = ["{}. [ ] {} \n\t- job name: {} \n\t-``sbatch {}`` ".format(i,case_tracker[i],batch_case_list_filepaths[i],job_name_list[i]) for i in range(len(job_name_list))]
    batch_case_list_filepath = os.path.join(batch_script_dir,"job_list_{}.md".format(batch_number))

    batch_case_list_contents = "\n".join(k for k in batch_case_list_lines)
    with open(batch_case_list_filepath,"w") as f:
        f.write(batch_case_list_contents)  
    print("saved summary file to {}".format(batch_case_list_filepath))

