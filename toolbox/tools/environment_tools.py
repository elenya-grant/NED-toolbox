from dotenv import load_dotenv,find_dotenv
import os
from toolbox import ROOT_DIR
main_results_dir = ""

def set_local_results_dir(dir: str):
    global main_results_dir
    main_results_dir = dir

def get_local_results_dir():
    global main_results_dir
    if main_results_dir is None or len(main_results_dir)<3:
        raise ValueError("Please provide local project results directory using `set_local_results_dir_dot_env`"
        "(`from toolbox.tools.environment_tools import set_local_results_dir_dot_env`) \n"
        "Ensure your project dir is set in the .env file")
    return main_results_dir

def set_local_results_dir_dot_env(path=None):
    if path and os.path.exists(path):
        load_dotenv(path)
    else:
        path = os.path.join(str(ROOT_DIR),".env")
        load_dotenv(path)
    MAIN_RESULTS_FOLDER = os.getenv("MAIN_RESULTS_FOLDER")
    if MAIN_RESULTS_FOLDER is not None:
        set_local_results_dir(MAIN_RESULTS_FOLDER)
        # r = find_dotenv(usecwd=True)
        # load_dotenv(r)
