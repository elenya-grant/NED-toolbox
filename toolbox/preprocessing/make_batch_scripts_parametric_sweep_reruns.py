import os
from toolbox import INPUT_DIR
import shutil


input_config_dir = os.path.join(str(INPUT_DIR),"v1-parametricsweep-offgrid-reruns")
input_files = os.listdir(input_config_dir)
input_files = [f for f in input_files if ".yaml" in f]

example_batch_script_filepath = os.path.join(str(INPUT_DIR),"batch-scripts","paramsweep_cost_reruns","template_file.sh")
batch_script_dir = os.path.join(str(INPUT_DIR),"batch-scripts","paramsweep_cost_reruns")

if not os.path.isdir(batch_script_dir):
    os.makedirs(batch_script_dir,exist_ok=True)

baseline_subsweeps = ["hybrid_renewables"]
batch_script_filename_list = []
job_name_list = []

for cost_file in input_files:
    filename = "psrerun_{}".format(cost_file.replace(".yaml",""))
    new_batch_script_filename = os.path.join(batch_script_dir,filename + ".sh")
    batch_script_filename_list.append(new_batch_script_filename)
    #copy template contents to new script
    shutil.copy(example_batch_script_filepath,new_batch_script_filename)
    with open(new_batch_script_filename,"r") as f:
        file_contents = f.read()
    new_jobname = "rerun-{}".format(filename)
    file_contents = file_contents.replace("rerunjobname",new_jobname)
    file_contents = file_contents.replace("costfilename.yaml",cost_file)
    job_name_list.append(new_jobname)

    with open(new_batch_script_filename, 'w') as f:
        f.write(file_contents)

batch_case_list_filepaths = ["NED-toolbox/{}".format(k.split("NED-toolbox/")[-1]) for k in batch_script_filename_list]
batch_case_list_lines = ["{}. [ ] {} \n\t-``sbatch {}`` \n\t- job nane: {}".format(i,input_files[i],batch_case_list_filepaths[i],job_name_list[i]) for i in range(len(job_name_list))]
batch_case_list_filepath = os.path.join(batch_script_dir,"job_list.md")

batch_case_list_contents = "\n".join(k for k in batch_case_list_lines)
with open(batch_case_list_filepath,"w") as f:
    f.write(batch_case_list_contents)  
[]