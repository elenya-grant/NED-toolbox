import os
from toolbox import INPUT_DIR
import shutil

input_config_dir = os.path.join(str(INPUT_DIR),"v1-baseline-offgrid-reruns")
input_files = os.listdir(input_config_dir)
input_files = [f for f in input_files if ".yaml" in f]

example_batch_script_filepath = os.path.join(str(INPUT_DIR),"batch-scripts","baseline_cost_reruns","template_file.sh")
batch_script_dir = os.path.join(str(INPUT_DIR),"batch-scripts","baseline_cost_reruns")
baseline_subsweeps = ["equal-sized","under-sized","over-sized"]

# # below is to test:
# baseline_subsweeps = ["equal-sized"]
# input_files = ["custom_rerun_ATB2025_weighted.yaml"]

batch_script_filename_list = []
job_name_list = []

if not os.path.isdir(batch_script_dir):
    os.makedirs(batch_script_dir,exist_ok=True)

input_file_tracker = []
for subsweep in baseline_subsweeps:
    for cost_file in input_files:
        filename = "{}_{}".format(subsweep,cost_file.replace(".yaml",""))
        new_batch_script_filename = os.path.join(batch_script_dir,filename + ".sh")

        #copy template contents to new script
        shutil.copy(example_batch_script_filepath,new_batch_script_filename)
        with open(new_batch_script_filename,"r") as f:
            file_contents = f.read()
        new_jobname = "rerun-{}".format(filename)
        file_contents = file_contents.replace("rerunjobname",new_jobname)
        file_contents = file_contents.replace("costfilename.yaml",cost_file)
        file_contents = file_contents.replace("subsweepname",subsweep)

        batch_script_filename_list.append(new_batch_script_filename)
        job_name_list.append(new_jobname)
        input_file_tracker.append(cost_file)
        with open(new_batch_script_filename, 'w') as f:
            f.write(file_contents)


batch_case_list_filepaths = ["NED-toolbox/{}".format(k.split("NED-toolbox/")[-1]) for k in batch_script_filename_list]
batch_case_list_lines = ["{}. [ ] {} \n\t- ``sbatch {}`` \n\t- job nane: {}".format(i,input_file_tracker[i],batch_case_list_filepaths[i],job_name_list[i]) for i in range(len(job_name_list))]
batch_case_list_filepath = os.path.join(batch_script_dir,"baseline_rerun_job_list.md")

batch_case_list_contents = "\n".join(k for k in batch_case_list_lines)
with open(batch_case_list_filepath,"w") as f:
    f.write(batch_case_list_contents)  
                    
[]