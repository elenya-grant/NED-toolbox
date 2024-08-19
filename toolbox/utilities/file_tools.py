import os
from pathlib import Path

def check_create_folder(filepath):
    if not os.path.isdir(filepath):
        os.makedirs(filepath,exist_ok=True)
        already_exists = False
    else:
        already_exists = True

    return already_exists