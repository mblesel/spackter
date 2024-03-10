import typer
import subprocess
import os
import yaml
from typing import Optional
from pathlib import Path


def run_shell_cmd(cmd: str, print_cmd=True, error_exit=True):
    if print_cmd:
        print("===> Running commands:")
        for command in cmd.split(';'):
            if command:
                print(f"  $ {command}")

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True) as proc:
        if proc.stdout:
            for line in proc.stdout:
                print(line)
        proc.communicate()
    result = subprocess.CompletedProcess(cmd, proc.returncode)
    if result.returncode:
        print(f"===> Error: {result.args} failed with return code {result.returncode}")
        if error_exit:
            print("Aborting.")
            raise typer.Exit(code=1)
        else: 
            return False
    else:
        return True


def get_spackter_root():
    spackter_root = os.environ.get('SPACKTER_ROOT', "")
    if not spackter_root:
        print(f"===> Error: SPACKTER_ROOT is not set. Aborting.")
        raise typer.Exit(code=1)
    return Path(spackter_root)


def read_stacks_file():
    spackter_root = get_spackter_root()
    spackter_stacks = spackter_root / "data/stacks.yaml"
    
    if spackter_stacks.exists():
        with open(spackter_stacks, "r") as file:
            return yaml.safe_load(file.read())
    else:
        return {}


def write_stacks_file(content: dict[str, dict]):
    spackter_root = get_spackter_root()
    spackter_data_dir = spackter_root / "data"
    spackter_stacks = spackter_data_dir / "stacks.yaml"

    if not spackter_data_dir.exists():
        spackter_data_dir.mkdir(parents=False, exist_ok=False)

    with open(spackter_stacks, "w") as file:
        file.write(yaml.safe_dump(content))


def select_stack(name: str, id: Optional[bool]):
    spackter_stacks = read_stacks_file()
    stacks = []
    if not id:
        for entry in spackter_stacks:
            if not entry == "data" and spackter_stacks[entry]["name"] == name:
                stacks.append((entry, spackter_stacks[entry]))
    else: 
        for entry in spackter_stacks:
            if not entry == "data" and spackter_stacks[entry]["id"] == int(name):
                stacks.append((entry, spackter_stacks[entry]))
    return stacks


def remove_stack(spack_root: Path):
    stacks = read_stacks_file()
    if stacks:
        if stacks.pop(spack_root.resolve().as_posix(), None):
            stacks["data"]["stack_count"] -= 1
            write_stacks_file(stacks)


