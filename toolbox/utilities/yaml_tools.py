from toolbox.utilities.yaml_loaders import BasicLoader, SmartLoader, SuperSmartLoader
import yaml

def load_yaml(filename, loader=SuperSmartLoader):
    with open(filename) as fid:
        return yaml.load(fid, loader)

def write_yaml(filename,data):
    if not '.yaml' in filename:
        filename = filename +'.yaml'

    with open(filename, 'w+') as file:
        yaml.dump(data, file,sort_keys=False,encoding = None,default_flow_style=False)
    return filename