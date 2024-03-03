import typer
from typing_extensions import Annotated
from typing import Optional
from pathlib import Path

import globals
from spackter_util import read_stacks_file
from spackter_util import write_stacks_file


def add(
    name: Annotated[str,
        typer.Argument(help=
        """
        Name for the spack stack.
        """
        )],
    spack_root: Annotated[Path,
        typer.Argument(help=
        """
        Path to the root directory of the spack stack.
        """
        )],
    env_script: Annotated[Optional[str],
        typer.Option("--env-script", help=
        """
        Path to the env script that shall be sourced when this stacked is loaded by spackter.
        Defaults to '<SPACK_ROOT>/share/spack/setup-env.sh'
        """,
        show_default=False)] = None
):
    spack_root = spack_root.expanduser().resolve()
    if not spack_root.exists():
        print(f"===> Directory does not exist: {spack_root}")
        print(f"===> Exiting.")
        raise typer.Exit(code=1)
    
    if not (spack_root / "bin/spack").exists():
        print(f"===> The given directory is not a spack installation: {spack_root}")
        print(f"===> Exiting.")
        raise typer.Exit(code=1)

    if env_script:
        env_script_path = Path(env_script).expanduser().resolve()
        if not env_script_path.exists():
            print(f"===> Could not find a env script at: {env_script_path}")
            print(f"===> Exiting.")
            raise typer.Exit(code=1)
    else:
        env_script_path = Path(spack_root / "share/spack/setup-env.sh").expanduser().resolve()
        if not env_script_path.exists():
            print(f"===> Could not find a default env script at: {env_script_path}")
            print(f"===> Exiting.")
            raise typer.Exit(code=1)

    print(f"===> Adding spack stack '{name}' from '{spack_root} to spackter database.")
    print(f"===> Following env script will be used when loading the stack: {env_script_path}")

    spackter_entry = {}
    spackter_entry["name"] = name
    spackter_entry["prefix"] = spack_root.parent.resolve().as_posix()
    spackter_entry["compiler"] = "UNKNOWN"
    spackter_entry["type"] = "EXTERN"
    spackter_entry["configs"] = "UNKNOWN"
    spackter_entry["env_script"] = env_script_path.resolve().as_posix()
    spackter_entry["created"] = "UNKNOWN"
    spackter_entry["post_install"] = {}
    spackter_entry["packages"] = []
    spackter_entry["pull_requests"] = []
    spackter_entry["patches"] = []
    spackter_entry["spack_version"] = "UNKNOWN VERSION"
    
    stacks = read_stacks_file()
    if stacks:
        if spack_root.resolve().as_posix() in stacks:
            print("===> Error: Could not add spack stack to spackter.")
            print(f"===> There already exists a spack stack at: {spack_root} ")
            print("===> Exiting.")
            raise typer.Exit(code=1)

        spackter_entry["id"] = stacks["data"]["id_counter"] + 1
        stacks[spack_root.resolve().as_posix()] = spackter_entry 
        stacks["data"]["id_counter"] += 1
        stacks["data"]["stack_count"] += 1
        write_stacks_file(stacks)
    else:
        stacks = {}
        stacks["data"] = {}
        stacks["data"]["stack_count"] = 1
        stacks["data"]["id_counter"] = 1
        stacks["data"]["spackter_version"] = __version__
        spackter_entry["id"] = 1
        stacks[spack_root.resolve().as_posix()] = spackter_entry
        write_stacks_file(stacks)
