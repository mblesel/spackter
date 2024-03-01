import typer
import yaml
from typing_extensions import Annotated
from typing import Optional
from rich import print
from rich.console import Console
from rich.table import Table
from rich.align import Align
from pathlib import Path
from datetime import date
import subprocess
import os
import shutil


spackter = typer.Typer()
console = Console()
__version__ = "0.1.1"


def get_allow_errors_options(allow_errors, no_allow_errors):
    allow_errors_options = {}
    
    if allow_errors:
        allow_options = allow_errors.split(",")
        if "all" in allow_options:
            allow_options = ["patch", "pr", "package", "script"]
    if no_allow_errors:
        no_allow_options = no_allow_errors.split(",")
        if "all" in no_allow_options:
            no_allow_options = ["patch", "pr", "package", "script"]


    if allow_errors and no_allow_errors:
        intersection = list(set(allow_options) & set(no_allow_options))
        if intersection:
            print(f"===> Error: --allow-errors and --no-allow-errors contain same options: {intersection}")
            raise typer.Exit(code=1)

    if allow_errors:
        for option in allow_options:
            if not option in ["patch", "pr", "package", "script"]:
                print(f"===> Error: Unknown option for --allow-errors: {option}")
                raise typer.Exit(code=1)

            allow_errors_options[option] = True

    if no_allow_errors:
        for option in no_allow_options:
            if not option in ["patch", "pr", "package", "script"]:
                print(f"===> Error: Unknown option for --no-allow-errors: {option}")
                raise typer.Exit(code=1)

            allow_errors_options[option] = False

    return allow_errors_options


def run_shell_cmd(cmd: str, print_cmd=True, error_exit=True):
    if print_cmd:
        print("===> Running commands:")
        for command in cmd.split(';'):
            if command:
                print(f"  $ {command}")

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True) as proc:
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


def apply_patch(file, spack_root, allow_errors_options):
    print(f"===> Applying {file.name}")
    cmd = f"cd {spack_root};"
    cmd += f"git apply --verbose {file};"
    result = run_shell_cmd(cmd, error_exit=False)
    if not result:
        if "patch" in allow_errors_options:
            if allow_errors_options["patch"]:
                print(f"===> Skipping patch: {file.name}")
            else:
                print("===> Exiting.")
                raise typer.Exit(code=1)
        elif not typer.confirm(f"===> Skip patch: {file.name}?"):
            print("===> Exiting.")
            raise typer.Exit(code=1)
    return result


def apply_pr(pr, spack_root, allow_errors_options):
    print(f"===> Applying PR {pr}")
    cmd = f"cd {spack_root};"
    cmd += f'curl --fail --location --remote-name "https://github.com/spack/spack/pull/{pr}.diff";'
    cmd += f"git apply --verbose {pr}.diff;"
    # TODO delete diff file while still getting error code from git apply command
    result = run_shell_cmd(cmd, error_exit=False)
    if not result:
        if "pr" in allow_errors_options:
            if allow_errors_options["pr"]:
                print(f"===> Skipping PR: {pr}")
            else:
                print("===> Exiting.")
                raise typer.Exit(code=1)
        elif not typer.confirm(f"===> Skip PR {pr}?"):
            print("===> Exiting.")
            raise typer.Exit(code=1)
    return result


def spack_install(base_cmd: str, package: str, compiler: str, allow_errors_options):
    print(f"===> Installing {package}")
    cmd = base_cmd + f"spack install {package}"
    if compiler:
        cmd += f" %{compiler}"
    cmd += ";"
    result = run_shell_cmd(cmd, error_exit=False)
    if not result:
        if "package" in allow_errors_options:
            if allow_errors_options["package"]:
                print(f"===> Skipping installing: {package}")
            else:
                print("===> Exiting.")
                raise typer.Exit(code=1)
        elif not typer.confirm(f"===> Skip installing {package}?"):
            print("Exiting.")
            raise typer.Exit(code=1)
    return result


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
        return None


def write_stacks_file(content):
    spackter_root = get_spackter_root()
    spackter_data_dir = spackter_root / "data"
    spackter_stacks = spackter_data_dir / "stacks.yaml"

    if not spackter_data_dir.exists():
        spackter_data_dir.mkdir(parents=False, exist_ok=False)

    with open(spackter_stacks, "w") as file:
        file.write(yaml.safe_dump(content))

def print_create_summary(spackter_entry):
    table = Table("Spackter create summary")
    t1 = Table(show_header=False)
    t2 = Table(title="Patches", show_header=False)
    t3 = Table(title="Pull Requests",show_header=False)
    t4 = Table(title="Packages", show_header=False)
    t5 = Table(title="Packages", show_header=False)

    t1.add_row("Name", spackter_entry['name'])
    t1.add_row("ID", f"{spackter_entry['id']}")
    t1.add_row("Location", spackter_entry['prefix'] + "/" + spackter_entry['name'])
    if spackter_entry["compiler"]:
        t1.add_row("Compiler", spackter_entry['compiler'])
    else:
        t1.add_row("Compiler", "System")
    t1.add_row("Spack version", spackter_entry['spack_version'])
    for patch in spackter_entry['patches']: 
        status = "SUCCESS" if patch[1] else "FAILED"
        t2.add_row(patch[0], status)
    for pr in spackter_entry['pull_requests']:
        status = "SUCCESS" if pr[1] else "FAILED"
        t3.add_row(pr[0], status)
    for pkg in spackter_entry['packages']:
        status = "SUCCESS" if pkg[1] else "FAILED"
        t4.add_row(pkg[0], status)
    status = "SUCCESS" if spackter_entry['post_install']['success'] else "FAILED"
    t5.add_row("Post install script", status)

    table.add_row(Align(t1, align="center"))
    table.add_row(Align(t2, align="center"))
    table.add_row(Align(t3, align="center"))
    table.add_row(Align(t4, align="center"))
    table.add_row(Align(t5, align="center"))
    console.print(table)
    print(f"===> Use 'spackter load' to activate the stack or manually source: {spackter_entry['env_script']}")


def print_compact_list(only_name: str = None):
    stacks = read_stacks_file()
    table = Table("NAME", "ID", "COMPILER", "CONFIGS", "SPACK VERSION", "TYPE", "CREATED")
    for entry in stacks:
        if not entry == "data":
            name = stacks[entry]["name"]
            id = stacks[entry]["id"]
            compiler = stacks[entry]["compiler"] if stacks[entry]["compiler"] else "system"
            configs =  stacks[entry]["configs"]
            spack_version =  stacks[entry]["spack_version"].split(" ")[0]
            type =  stacks[entry]["type"]
            created = stacks[entry]["created"]
            if only_name:
                if only_name == name:
                    table.add_row(name, f"{id}", compiler, configs, spack_version, type, created)
            else:
                table.add_row(name, f"{id}", compiler, configs, spack_version, type, created)
    console.print(table)


def select_stack(name, id: bool):
    spackter_stacks = read_stacks_file()
    stacks = []
    if not id:
        for entry in spackter_stacks:
            if not entry == "data" and spackter_stacks[entry]["name"] == name:
                stacks.append(spackter_stacks[entry])
    else: 
        for entry in spackter_stacks:
            if not entry == "data" and spackter_stacks[entry]["id"] == int(name):
                stacks.append(spackter_stacks[entry])
    return stacks


def remove_stack(spack_root: Path):
    stacks = read_stacks_file()
    if stacks:
        if stacks.pop(spack_root.resolve().as_posix(), None):
            stacks["data"]["stack_count"] -= 1
            write_stacks_file(stacks)
    

def version_callback(value: bool):
    if value:
        print(f"spackter v{__version__}")
        raise typer.Exit()


# TODO also allow rename?
@spackter.command(help=
    """
    NOT YET IMPLEMENTED
    """
)
def move():
    print("===> TODO")


# TODO mark as external
# TODO option for env.sh file (default to spack's setup-env.sh)
@spackter.command(help=
    """
    NOT YET IMPLEMENTED
    """
)
def add():
    print("===> TODO")


# TODO --yes-to-all?
@spackter.command(help=
    """
    Deletes a spack stack.
    --only-spackter-entry can be set to only remove the spackter database entry and not delete the spack stack from disk.
    """
)
def delete(
    name: Annotated[str, 
        typer.Argument(help=
        """
        Name of spack stack, or ID of spack stack if '--id' option is given.
        """
        )],
    id: Annotated[Optional[bool],
        typer.Option("--id", help=
        """
        ID of spack stack. Needed if two stack with same name exist at different prefixes.
        """
        )] = False,
    only_spackter_entry: Annotated[Optional[bool],
        typer.Option("--only-spackter-entry", help=
        """
        Only remove the spack stack entry from spackter database and do not delete from disk.
        """
        )] = False
):
    selected = select_stack(name, id)
    if not selected:
        if id:
            print(f"===> Could not find a spack stack with the id '{name}'.")
        else:
            print(f"===> Could not find a spack stack with the name '{name}'.")
        print("===> Aborting.")
        raise typer.Exit(code=1)
    elif len(selected) > 1:
        print(f"===> There are multiple spack stacks with the name '{name}':")
        print_compact_list(only_name=name)
        print("===> Use 'spackter load <id> --id' to specify the intended spack stack.")
        print(f"===> Aborting.")
        raise typer.Exit(code=1)
    else:
        stack = selected[0]
        spack_root = Path(selected[0]["prefix"] + "/" + selected[0]["name"])
        if not only_spackter_entry and spack_root.exists():
            if typer.confirm(f"===> Delete '{spack_root}' from disk?"):
                shutil.rmtree(spack_root)
                print(f"===> '{spack_root}' deleted.")
        print(f"===> Removing '{selected[0]['name']}' from spackter database.")
        remove_stack(spack_root)


# TODO how does spack load work?
@spackter.command(help=
    """
    Outputs the location of the 'env.sh' script that needs to be sourced to activate 
    the given spack stack.
    """
)
def load(
    name: Annotated[str, 
        typer.Argument(help=
        """
        Name of spack stack, or ID of spack stack if '--id' option is given.
        """
        )],
    id: Annotated[Optional[bool],
        typer.Option("--id", help=
        """
        ID of spack stack. Needed if two stack with same name exist at different prefixes.
        """
        )] = False,
    only_env_script: Annotated[Optional[bool], typer.Option("--only-env-script")] = False
):
    selected = select_stack(name, id)
    if not selected:
        if id:
            print(f"===> Could not find a spack stack with the id '{name}'.")
        else:
            print(f"===> Could not find a spack stack with the name '{name}'.")
        print("===> Aborting.")
        raise typer.Exit(code=1)
    elif len(selected) > 1:
        print(f"===> There are multiple spack stacks with the name '{name}':")
        print_compact_list(only_name=name)
        print("===> Use 'spackter load <id> --id' to specify the intended spack stack.")
        print(f"===> Aborting.")
        raise typer.Exit(code=1)
    else:
        stack = selected[0]
        if not only_env_script:
            print(f"===> Loading spack stack: {stack['name']} (ID {stack['id']})")
            print("===> Source this environment script:")
            print(f"{stack['env_script']}")
        else:
            print(f"{stack['env_script']}")
        

# TODO --long and --format
@spackter.command(help=
    """
    Lists all currently installed spack stacks.
    """
)
def list():
    print_compact_list()


# TODO Move individual actions into functions?
# TODO clone specific spack branch
# TODO spack mirrors
# TODO see if typer has something for possible values of an option
@spackter.command(help=
    """
    Create a new spack stack with a given name.
    'SPACKTER_ROOT/configs' contains directories with spack and spackter 
    configurations files which are used during creation.
    See 'default' and 'test' directories for examples.
    """
)
def create(
    name: Annotated[str,
        typer.Argument(help=
        """Name for the spack stack""",
        show_default=False)],
    configs: Annotated[str, 
        typer.Option(help=
        """
        Name of configs directory inside 'SPACKTER_ROOT/configs'
        """ 
        )] = "default",
    prefix: Annotated[Optional[str],
        typer.Option(help=
        """
        Install prefix path for this spack stack. Defaults to 'SPACKTER_ROOT/spack'
        """,
        show_default=False)] = None,
    compiler: Annotated[Optional[str],
        typer.Option(help=
        """
        Specify compiler that spack will build and use for packages.
        Defaults to first system compiler that spack finds
        """,
        show_default=False)] = None,
    allow_errors: Annotated[Optional[str], 
        typer.Option("--allow-errors", help=
        """
        Will ignore errors for specified phases.
        Takes comma separated string of: ['all', 'patch', 'pr', 'package', 'script']
        """,
        show_default=False)] = None,
    no_allow_errors: Annotated[Optional[str],
        typer.Option("--no-allow-errors", help=
        """
        Will abort when encountering error in specified phases. 
        Takes comma separated string of: ['all', 'patch', 'pr', 'package', 'script']
        """,
        show_default=False)] = None,
):
    ## 
    ## Check arguments and env vars
    ##
    spackter_root = get_spackter_root()

    spackter_config_dir = spackter_root / "configs" / configs
    if not spackter_config_dir.exists():
        print(f"===> Error: Spackter configs dir does not exist at: {spackter_config_dir}")
        print("===> Aborting.")
        raise typer.Exit(code=1)

    if not prefix:
        print(f"===> No prefix given.") 
        prefix = spackter_root / "spack"
        print(f"===> Using default prefix: {prefix}") 
    else:
        prefix = Path(prefix).expanduser().resolve()

    spack_root = prefix / name

    # Check --allow-errors and --no-allow-errors options
    allow_errors_options = get_allow_errors_options(allow_errors, no_allow_errors)

    ##
    ## Create fresh spack repo
    ##
    prefix.mkdir(parents=True, exist_ok=True)
    if spack_root.exists():
        if typer.confirm("===> " + spack_root.resolve().as_posix() + " already exists. Overwrite it?"):
            shutil.rmtree(spack_root)
            remove_stack()
        else:
            print("===> Exiting")
            raise typer.Exit()

    print(f"===> Creating new spack stack at: {spack_root}")
    cmd = "git clone https://github.com/spack/spack.git " + spack_root.resolve().as_posix()
    run_shell_cmd(cmd)

    # Stores information about the spack stack that will be remembered by spackter
    spackter_entry = {}

    ##
    ## Apply patches
    ##
    spackter_entry["patches"] = []
    spackter_patch_dir = spackter_config_dir / "patches"
    if spackter_patch_dir.exists():
        patch_files = spackter_patch_dir.glob('*.patch')
        if patch_files:
            print(f"===> Applying patches from: {spackter_patch_dir}")
            for file in patch_files:
                result = apply_patch(file, spack_root, allow_errors_options)
                if result:
                    spackter_entry["patches"].append((file.name, True))
                else:
                    spackter_entry["patches"].append((file.name, False))
        else:
            print("===> No patches to apply.")
    else:
        print(f"No 'patch' dir found at: {spackter_patch_dir}")
        print("===> No patches to apply.")

    ##
    ## Apply pull requests
    ##
    spackter_entry["pull_requests"] = []
    pr_file = spackter_config_dir / "pull-requests.spackter"
    if pr_file.exists():
        print(f"===> Applying pull requests from: {pr_file}")
        with open(pr_file, "r") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    result = apply_pr(line, spack_root, allow_errors_options)
                    if result:
                        spackter_entry["pull_requests"].append((line, True))
                    else:
                        spackter_entry["pull_requests"].append((line, False))
    else:
        print(f"===> No pull-requests file found at: {pr_file}")
        print("===> No pull requests will be applied.")

    ##
    ## Copy spack config files
    ##
    spack_config_dir = spack_root / "etc/spack"
    print(f"===> Copying spack configuration files to {spack_config_dir}")
    config_files = spackter_config_dir.glob('*.yaml')
    for file in config_files:
        print(f"===> Copying: {file.name}")
        shutil.copyfile(file, spack_config_dir / file.name)


    ##
    ## Basic commands required to run a spack command 
    ##
    spack_env_script = spack_root / "share/spack/setup-env.sh"
    base_cmd = "export SPACK_DISABLE_LOCAL_CONFIG=1;"
    base_cmd += f". {spack_env_script};"

    ##
    ## Install Compiler if needed
    ##
    if compiler:
        cmd = base_cmd + f"spack install {compiler};"
        cmd += f"export location=$(spack location --install-dir {compiler});"
        cmd += "spack compiler find ${location};"
        print("===> Installing Compiler:")
        run_shell_cmd(cmd)

    ##
    ## Install packages
    ##
    spackter_entry["packages"] = []
    package_list = spackter_config_dir / "package-list.spackter"
    if package_list.exists():
        with open(package_list, "r") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    result = spack_install(base_cmd, line, compiler, allow_errors_options)
                    if result:
                        spackter_entry["packages"].append((line,True))
                    else:
                        spackter_entry["packages"].append((line,False))
    else:
        print(f"===> No package list file found at: {package_list}")
        print("===> No packages will be installed.")


    ##
    ## Final steps of spack stack creation
    ##

	# Remove all unneeded packages
    cmd = base_cmd + "spack gc --yes-to-all;"
    run_shell_cmd(cmd)
    # Run post-install-script
    spackter_entry["post_install"] = {}
    post_install_script = spackter_config_dir / "post-install-script.spackter"
    if not post_install_script.exists():
        print(f"===> No spackter post-install-script found at: {post_install_script}")
        print("===> Skipping post-install-script execution.")
    else:
        print(f"===> Running spackter post-install-script at: {post_install_script}")
        cmd = f"cd {spack_root};"
        cmd += f"bash -e -x {post_install_script};"
        result = run_shell_cmd(cmd, error_exit=False)
        if not result:
            if "script" in allow_errors_options:
                if allow_errors_options["script"]:
                    print(f"===> Ignoring errors in post-install-script.")
                else:
                    print("===> Exiting.")
                    raise typer.Exit(code=1)
            elif not typer.confirm(f"===> Ignore errors in post-install-script?"):
                print("===> Exiting.")
                raise typer.Exit(code=1)
            spackter_entry["post_install"]["success"] = False
        else:
            spackter_entry["post_install"]["success"] = True
        with open(post_install_script, "r") as file:
            content = file.read()
            spackter_entry["post_install"]["content"] = content


    ##
    ## Generate env.sh script for this spack stack
    ##
    pre_script_path = spackter_config_dir / "pre-script.spackter"
    post_script_path = spackter_config_dir / "post-script.spackter"
    if not pre_script_path.exists():
        print("===> No spackter pre-script found at: {pre_script_path}")
        print("===> Using default pre-script.")
        pre_script_path = spackter_config_dir / "default/pre-script.spackter"
    if not post_script_path.exists():
        print("===> No spackter post-script found at: {post_script_path}")
        print("===> Using default post-script.")
        post_script_path = spackter_config_dir / "default/post-script.spackter"

    pre_script = open(pre_script_path, "r")
    post_script = open(post_script_path, "r")
    env_script = pre_script.read() + f". {spack_env_script}\n" + post_script.read()
    pre_script.close()
    post_script.close()

    print(f"===> Generating 'env.sh' script at: {spack_root}/env.sh")
    with open(spack_root / "env.sh", "w") as file:
        file.write(env_script)
        print(env_script)

    ##
    ## Create spackter entry for this spack stack
    ##
    # s_root = spack_root.resolve().as_posix()
    spackter_entry["name"] = name
    spackter_entry["prefix"] = prefix.resolve().as_posix()
    spackter_entry["compiler"] = compiler
    spackter_entry["type"] = "SPACKTER"
    spackter_entry["configs"] = configs
    spackter_entry["env_script"] = (spack_root / "env.sh").resolve().as_posix()
    spackter_entry["created"] = f"{date.today()}"
    
    cmd = base_cmd + "spack --version;"
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True) 
    spackter_entry["spack_version"] = result.stdout.strip()

    # Save the entry
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

    ##
    ## Summary of spack stack creation
    ##
    print_create_summary(spackter_entry)
    
    # TODO when implementing mirrors
	# if test -n "${BOOTSTRAP_MIRROR}"
	# then
	# 	# Remove cached downloads, which are also available in the mirror
	# 	./bin/spack clean --downloads
	# fi




@spackter.callback(help=
    """
    Spackter is a tool for the creation and management of multiple spack stacks on the same system.
    Creation of new spack stacks can be configured in depth via multiple configuration files.
    Examples can be found at 'SPACKTER_ROOT/configs'.
    """
)
def main(version: Annotated[Optional[bool], typer.Option("--version", callback=version_callback, is_eager=True)] = None):
    todo = "todo"
    # print(f"spackter v{__version__}")


if __name__ == "__main__":
    spackter()
