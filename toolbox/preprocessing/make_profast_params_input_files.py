from toolbox import LIB_DIR
from toolbox import INPUT_DIR
import os
import pandas as pd
from toolbox.utilities.yaml_tools import load_yaml,write_yaml
from attrs import define, field
from toolbox.utilities.file_tools import check_create_folder
from toolbox.simulation.ned_base import BaseClassNed
import shutil


finance_dir = os.path.join(str(LIB_DIR),"finance")
profast_template_filename = "profast_config_onshore_v1_template.yaml"
profast_template_filepath = os.path.join(finance_dir,profast_template_filename)
finance_param_template_mapper = {
    "leverage after tax nominal discount rate":"rroe",
    "debt equity ratio of initial financing":"der",
    "debt interest rate":"rdir"}

finance_param_opt_descriptions = ["B","H","R"] #B: Baseline H: Hydrogen R: Renewables
finance_param_options = {
    "leverage after tax nominal discount rate":[0.0948,0.1089,0.0615],
    "debt equity ratio of initial financing":[1.72,0.62,2.82],
    "debt interest rate":[0.046,0.05,0.0439]}

finance_case_list = []
finance_case_num = []
cnt = 0
for i_rroe,rroe in enumerate(finance_param_options["leverage after tax nominal discount rate"]):
    rroe_case = finance_param_opt_descriptions[i_rroe]
    for i_der,der in enumerate(finance_param_options["debt equity ratio of initial financing"]):
        der_case = finance_param_opt_descriptions[i_der]
        for i_rdir,rdir in enumerate(finance_param_options["debt interest rate"]):
            rdir_case = finance_param_opt_descriptions[i_rdir]
            new_profast_filename = "profast_config_v1_{}rroe_{}der_{}rdir.yaml".format(rroe_case,der_case,rdir_case)
            new_profast_filepath = os.path.join(finance_dir,new_profast_filename)
            # copy template to file
            shutil.copy(profast_template_filepath,new_profast_filepath)
            #read in new file
            with open(new_profast_filepath,"r") as f:
                file_contents = f.read()
            file_contents = file_contents.replace("rroe",str(rroe))
            file_contents = file_contents.replace("der",str(der))
            file_contents = file_contents.replace("rdir",str(rdir))
            with open(new_profast_filepath, 'w') as f:
                f.write(file_contents)
            

            finance_case_list.append(new_profast_filename)
            finance_case_num.append(cnt)
            cnt+=1
fin_case_dict = dict(zip(finance_case_num,finance_case_list))

finance_case_info_filepath = os.path.join(finance_dir,"FinanceReRun_Summary.yaml")
write_yaml(finance_case_info_filepath,fin_case_dict)