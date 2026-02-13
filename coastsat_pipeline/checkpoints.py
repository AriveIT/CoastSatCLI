import pickle

# saved (and assumed) checkpoint pkl file names are <stage_name>.pkl

def save_context(context, stage_name):
    filename = get_cp_directory() + '/' + get_file_name_from_stage_name(stage_name)
    with open(filename, 'wb') as f:
        pickle.dump(context, f)

def load_context(stage_name):
    filename = get_cp_directory() + '/' + get_file_name_from_stage_name(stage_name)
    try:
        with open(filename, 'rb') as f:
            return pickle.load(f)
    except Exception:
        print(f"No checkpoint for stage with name \"{stage_name}\" found in {get_cp_directory()} directory")
        exit()

###############################################################################################
# The following functions are for organizing the name of the pkl files and where they're stored
# This way, if that ever needs to be changed, ONLY these functions need altering
###############################################################################################
def get_stage_name_from_file_name(file_name):
    # pkl files have format <stage_name>.pkl so want everything before the .
    return file_name.split(".")[0]

def get_file_name_from_stage_name(stage_name):
    return stage_name + ".pkl"

def get_cp_directory():
    return "checkpoints"