from pathlib import Path
import os 

def get_toxworkdir_subdir(subdir:str) -> Path:
    dir = Path(os.environ['TOX_WORK_DIR']).joinpath(subdir) \
        if os.environ.get('TOX_WORK_DIR') else Path(os.getcwd()).joinpath(f'./.tox/{subdir}')
    assert dir.exists(), f"Looks like {dir} not not exist!"
    return dir
