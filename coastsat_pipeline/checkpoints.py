import pickle    
import re

# saved (and assumed) checkpoint pkl files names are <stage_name>.pkl

def save_context(context, stage_name):
    filename = get_cp_directory() + '/' + stage_name + ".pkl"
    with open(filename, 'wb') as f:
        pickle.dump(context, f)

def load_context(stage_name):
    filename = get_cp_directory() + '/' + stage_name + ".pkl"
    try:
        with open(filename, 'rb') as f:
            return pickle.load(f)
    except Exception:
        print(f"No checkpoint for stage with name \"{stage_name}\" found in {get_cp_directory()} directory")
        exit()

def get_stage_name_from_file_name(file_name):
    # pkl files have format <stage_name>.pkl so want everything before the .
    # indexing removes - (simplifies regex)
    return re.search(r'.*\.', file_name).group()[:-1]

def get_cp_directory():
    return "checkpoints"