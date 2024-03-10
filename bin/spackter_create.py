import typer

import shutil
import requests
import subprocess

from typing_extensions import Annotated
from typing import Optional
from typing import Union
from pathlib import Path
from datetime import date
from git import Repo
from rich.table import Table
from rich.align import Align


from globals import __version__
from globals import console

from spackter_util import get_spackter_root
from spackter_util import run_shell_cmd
from spackter_util import remove_stack
from spackter_util import write_stacks_file
from spackter_util import read_stacks_file



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
    prefix: Annotated[Optional[Path],
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
    create_mirror: Annotated[Optional[str],
        typer.Option("--create-mirror", help=
        """
        Creates a mirror for all installed packages at the given path.
        If the directory at the given path already exists it will be deleted!
        """,
        show_default=False)] = None,
    with_mirror: Annotated[Optional[str],
        typer.Option("--with-mirror", help=
        """
        Will use the path to a given mirror as spack mirror during stack creation.
        """,
        show_default=False)] = None, 
    spack_branch: Annotated[Optional[str],
        typer.Option("--spack_branch", help=
        """
        Will use the given spack branch for stack creation.
        """,
        show_default=False)] = None,
    spack_commit: Annotated[Optional[str],
        typer.Option("--spack_commit", help=
        """
        Will use the given spack commit for stack creation.
        """,
        show_default=False)] = None
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
        prefix = prefix.expanduser().resolve()

    spack_root = prefix / name

    # Check --allow-errors and --no-allow-errors options
    allow_errors_options = get_allow_errors_options(allow_errors, no_allow_errors)

    # Check mirror options
    if create_mirror and with_mirror:
        print("===> --create-mirror and --with-mirror can not noth be set.")
        print("===> Exiting.")
        raise typer.Exit(code=1)
    # Check create_mirror
    mirror_path = None
    if create_mirror:
        mirror_path = Path(create_mirror).expanduser().resolve()
    # Check with_mirror
    with_mirror_path = None
    if with_mirror:
        with_mirror_path = Path(with_mirror).expanduser().resolve()

    # Check branch and commit options
    if spack_branch and spack_commit:
        print("===> --spack-branch and --spack-commit can not both be set.")
        print("===> Exiting.")
        raise typer.Exit(code=1)

    ##
    ## Install the spack stack
    ##
    ## Create fresh spack repo
    spack_repo = clone_spack(prefix, spack_root, spack_branch, spack_commit)
    # Stores information about the spack stack that will be remembered by spackter
    spackter_entry = {}
    ## Apply patches
    spackter_entry["patches"] = handle_patches(spackter_config_dir, spack_repo, allow_errors_options)
    ## Apply pull requests
    spackter_entry["pull_requests"] = handle_prs(spackter_config_dir, spack_repo, allow_errors_options)
    ## Copy spack config files
    copy_config_files(spack_root, spackter_config_dir)

    ## Basic commands required to run a spack command 
    spack_env_script = spack_root / "share/spack/setup-env.sh"
    base_cmd = "export SPACK_DISABLE_LOCAL_CONFIG=1;"
    base_cmd = "export SPACK_USER_CACHE_PATH={spack_root}/cache;"
    base_cmd += f". {spack_env_script};"
    ## Handle mirrors
    handle_mirror(mirror_path, with_mirror_path, base_cmd)
    ## Install Compiler if needed
    handle_compiler(compiler, base_cmd)
    ## Install packages
    spackter_entry["packages"] = handle_packages(spackter_config_dir, base_cmd, compiler,
                                                 mirror_path, allow_errors_options)
    ## Final steps of spack stack creation
    spackter_entry["post_install"] = handle_epilogue(base_cmd, mirror_path, spackter_config_dir, 
                                                     spack_root, allow_errors_options)
    ## Generate env.sh script for this spack stack
    generate_env_script(spackter_config_dir, spack_root, spack_env_script)
    ## Create spackter entry for this spack stack
    create_spackter_entry(spackter_entry, name, prefix, compiler, configs, spack_root, base_cmd)
    ## Summary of spack stack creation
    print_create_summary(spackter_entry)


def clone_spack(prefix: Path,
                spack_root: Path, 
                spack_branch: Optional[str],
                spack_commit: Optional[str]) -> Repo:
    prefix.mkdir(parents=True, exist_ok=True)
    if spack_root.exists():
        if typer.confirm("===> " + spack_root.resolve().as_posix() + " already exists. Overwrite it? (This will delete the whole directory)"):
            shutil.rmtree(spack_root)
            remove_stack(spack_root)
        else:
            print("===> Exiting")
            raise typer.Exit()

    print(f"===> Creating new spack stack at: {spack_root}")
    if spack_branch:
        spack_repo = Repo.clone_from("https://github.com/spack/spack.git", spack_root.resolve().as_posix(), multi_options=[f'--branch {spack_branch}'])
    else:
        spack_repo = Repo.clone_from("https://github.com/spack/spack.git", spack_root.resolve().as_posix())
        if spack_commit:
            spack_repo.head.reference = spack_repo.create_head("spackter", f"{spack_commit}")
            spack_repo.head.reset(index=True, working_tree=True)

    return spack_repo


def handle_patches(spackter_config_dir: Path,
                   spack_repo: Repo,
                   allow_errors_options: dict[str, bool]) -> list[tuple[str, bool]]:
    patches = []
    spackter_patch_dir = spackter_config_dir / "patches"
    if spackter_patch_dir.exists():
        patch_files = spackter_patch_dir.glob('*.patch')
        if patch_files:
            print(f"===> Applying patches from: {spackter_patch_dir}")
            for file in patch_files:
                result = apply_patch(file, spack_repo, allow_errors_options)
                if result:
                    patches.append((file.name, True))
                else:
                    patches.append((file.name, False))
        else:
            print("===> No patches to apply.")
    else:
        print(f"No 'patch' dir found at: {spackter_patch_dir}")
        print("===> No patches to apply.")
    return patches


def handle_prs(spackter_config_dir: Path, 
               spack_repo: Repo,
               allow_errors_options: dict[str, bool]) -> list[tuple[str, bool]]:
    pr_file = spackter_config_dir / "pull-requests.spackter"
    prs = []
    if pr_file.exists():
        print(f"===> Applying pull requests from: {pr_file}")
        with open(pr_file, "r") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    result = apply_pr(line, spack_repo, allow_errors_options)
                    if result:
                        prs.append((line, True))
                    else:
                        prs.append((line, False))
    else:
        print(f"===> No pull-requests file found at: {pr_file}")
        print("===> No pull requests will be applied.")
    return prs


def copy_config_files(spack_root: Path, spackter_config_dir: Path):
    spack_config_dir = spack_root / "etc/spack"
    print(f"===> Copying spack configuration files to {spack_config_dir}")
    config_files = spackter_config_dir.glob('*.yaml')
    for file in config_files:
        print(f"===> Copying: {file.name}")
        shutil.copyfile(file, spack_config_dir / file.name)


def handle_mirror(mirror_path: Optional[Path],
                  with_mirror_path: Optional[Path],
                  base_cmd: str):
    # --create_mirror option
    if mirror_path:
        if mirror_path.exists():
            print(f"===> There already exists a directory at the given mirror path: {mirror_path}")
            if typer.confirm(f"Overwrite it? (This will delete the whole directory)"):
                shutil.rmtree(mirror_path)
            else:
                print("===> Exiting.")
                raise typer.Exit()
        mirror_path.mkdir(parents=True, exist_ok=False)
        
        # Add mirror to spack
        cmd = base_cmd + f"spack mirror add local file://{mirror_path}"
        print(mirror_path)
        print("===> Adding mirror to spack:")
        run_shell_cmd(cmd)
    else:
        print("===> No mirror will be created")

    # --with-mirror option
    if with_mirror_path:
        if with_mirror_path.exists():
            print(f"===> Using mirror at: {with_mirror_path}")
            # Add mirror to spack
            cmd = base_cmd + f"spack mirror add local file://{with_mirror_path}"
            print(with_mirror_path)
            print("===> Adding mirror to spack:")
            run_shell_cmd(cmd)
        else:
            print(f"===> Mirror was not found at: {with_mirror_path}")
            print("===> Exiting.")
            raise typer.Exit(code=1)


def handle_compiler(compiler: Optional[str], base_cmd: str):
    if compiler:
        cmd = base_cmd + f"spack install {compiler};"
        cmd += f"export location=$(spack location --install-dir {compiler});"
        cmd += "spack compiler find ${location};"
        print("===> Installing Compiler:")
        run_shell_cmd(cmd)


def handle_packages(spackter_config_dir: Path, 
                    base_cmd: str,
                    compiler: Optional[str],
                    mirror_path: Optional[Path],
                    allow_errors_options: dict[str, bool]) -> list[tuple[str, bool]]:
    packages = []
    package_list = spackter_config_dir / "package-list.spackter"
    if package_list.exists():
        with open(package_list, "r") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    result = spack_install(base_cmd, line, compiler, mirror_path, allow_errors_options)
                    if result:
                        packages.append((line,True))
                    else:
                        packages.append((line,False))
    else:
        print(f"===> No package list file found at: {package_list}")
        print("===> No packages will be installed.")
    return packages


def handle_epilogue(base_cmd: str,
                    mirror_path: Optional[Path],
                    spackter_config_dir: Path,
                    spack_root: Path,
                    allow_errors_options: dict[str, bool]) -> dict[str, Union[bool, str]]:
	# Remove all unneeded packages
    cmd = base_cmd + "spack gc --yes-to-all;"
    run_shell_cmd(cmd)

    # Remove cached downloads, which are also available in the mirror
    if mirror_path:
        cmd = base_cmd + "spack clean --downloads"
        run_shell_cmd(cmd)

    # Run post-install-script
    post_install = handle_post_install_script(spackter_config_dir, spack_root, allow_errors_options)
    return post_install


def handle_post_install_script(spackter_config_dir: Path,
                               spack_root: Path,
                               allow_errors_options: dict[str, bool]) -> dict[str,Union[bool, str]]:
    post_install = {}
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
            post_install["success"] = False
        else:
            post_install["success"] = True
        with open(post_install_script, "r") as file:
            content = file.read()
            post_install["content"] = content
    return post_install


def generate_env_script(spackter_config_dir: Path,
                        spack_root: Path,
                        spack_env_script: Path):
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


def create_spackter_entry(spackter_entry: dict[str,Union[str,bool,Union[str,bool,int]]],
                          name: str,
                          prefix: Path,
                          compiler: Optional[str],
                          configs: str,
                          spack_root: Path,
                          base_cmd: str):
    spackter_entry["name"] = name
    spackter_entry["prefix"] = prefix.resolve().as_posix()
    spackter_entry["compiler"] = compiler if compiler else ""
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


def get_allow_errors_options(allow_errors, no_allow_errors):
    allow_errors_options = {}
    allow_options = []
    no_allow_options = []
    
    if allow_errors:
        allow_options = allow_errors.split(",")
        if "all" in allow_options:
            allow_options = ["patch", "pr", "package", "script"]
    if no_allow_errors:
        no_allow_options = no_allow_errors.split(",")
        if "all" in no_allow_options:
            no_allow_options = ["patch", "pr", "package", "script"]


    if allow_errors and no_allow_errors:
        intersection = set(allow_options) & set(no_allow_options)
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


def apply_patch(file, spack_repo, allow_errors_options):
    print(f"===> Applying {file.name}")
    try:
        cmd = ['git', 'apply', '--verbose', f'{file.resolve().as_posix()}']
        result = spack_repo.git.execute(cmd, with_extended_output=True)
        print(result[1])
        print(result[2])
        return True
    except Exception as e:
        print(e)
        if "patch" in allow_errors_options:
            if allow_errors_options["patch"]:
                print(f"===> Skipping patch: {file.name}")
            else:
                print("===> Exiting.")
                raise typer.Exit(code=1)
        elif not typer.confirm(f"===> Skip patch: {file.name}?"):
            print("===> Exiting.")
            raise typer.Exit(code=1)
        return False


def apply_pr(pr, spack_repo, allow_errors_options):
    print(f"===> Applying PR {pr}")
    # TODO delete diff file while still getting error code from git apply command
    pr_data = requests.get(f"https://github.com/spack/spack/pull/{pr}.diff")
    with open (f"{spack_repo.working_dir}/{pr}.diff", "w") as file:
        file.write(pr_data.text)
    try:
        cmd = ['git', 'apply', '--verbose', f'{pr}.diff']
        result = spack_repo.git.execute(cmd , with_extended_output=True)
        print(result[1])
        print(result[2])
        return True
    except Exception as e:
        print(e)
        if "pr" in allow_errors_options:
            if allow_errors_options["pr"]:
                print(f"===> Skipping PR: {pr}")
                return False
            else:
                print("===> Exiting.")
                raise typer.Exit(code=1)
        elif not typer.confirm(f"===> Skip PR {pr}?"):
            print("===> Exiting.")
            raise typer.Exit(code=1)
        return False


def spack_install(base_cmd: str, package: str, compiler: Optional[str], mirror: Optional[Path], allow_errors_options):
    print(f"===> Installing {package}")
    result_mirror = True
    if mirror:
        cmd = base_cmd + f'spack mirror create --directory "{mirror}" --dependencies {package};'
        result_mirror = run_shell_cmd(cmd, error_exit=False)

    cmd = base_cmd + f"spack install {package}"
    if compiler:
        cmd += f" %{compiler}"
    cmd += ";"
    result = run_shell_cmd(cmd, error_exit=False)
    if (not result) or (not result_mirror):
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
