"""
NOTE: the coastsat pipeline often uses files that were made previously in the pipeline (jpgs for example)
If those files do not exist, this checkpoint system will not work
Therefore, recommended usage is to use checkpoints that you have created from your own runs, to guarantee
that those previous files have been created.

NOTE: always assumes pkl files are in checkpoints directory (this is where they get saved to and loaded from by checkpoints.py)

NOTE: pkl files are saved in runner.py BEFORE the corresponding stage is run
"""

from coastsat_pipeline.registry import default_stages
from coastsat_pipeline.runner import PipelineRunner

from coastsat_pipeline.checkpoints import load_context, get_cp_directory, get_stage_name_from_file_name
import os # file manipulation
import sys # command line args

# runs pipeline starting at target stage
def run_from_cp(target_stage_name) -> None:
    context = load_context(target_stage_name)
    stages_to_run = _get_stages_to_run(target_stage_name)

    # run remainder of pipeline, starting at target stage
    print(f"Running from stage: {target_stage_name}")
    runner = PipelineRunner(stages_to_run)
    runner.run(context)

# runs pipeline starting at stage associated with context pkl file with the most recent
# last modified date
def run_from_last_cp():
    context_file_name = _get_last_cp()
    target_stage_name = get_stage_name_from_file_name(context_file_name)
    context = load_context(target_stage_name)

    stages_to_run = _get_stages_to_run(target_stage_name)

    # run remainder of pipeline, starting at target stage
    print(f"Running from stage: {target_stage_name}")
    runner = PipelineRunner(stages_to_run)
    runner.run(context)

# gets checkpoint with most recent modification time
def _get_last_cp():
    dir = get_cp_directory()
    most_recent_time = -1
    most_recent_cp = ""
    for f in os.scandir(dir):
        if f.name == ".gitignore": continue
        if f.is_file(): # f can be a directory
            mtime = f.stat().st_mtime # modification time
            if mtime > most_recent_time:
                most_recent_time = mtime
                most_recent_cp = f.name
    return most_recent_cp

# return stages following (and including) target stage
def _get_stages_to_run(target_stage_name):
    all_stages = default_stages()
    stages_to_run = []
    for i in range(len(all_stages)):
        if all_stages[i].name == target_stage_name:
            # include target stage, since pkl file comes from before stage is run
            stages_to_run = all_stages[i:]
            break
    return stages_to_run

if __name__ == "__main__":
    if len(sys.argv) == 1:
        run_from_last_cp()
    else:
        run_from_cp(sys.argv[1])