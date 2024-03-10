import typer
from typing import Optional
from typing_extensions import Annotated
from rich.table import Table
from rich.align import Align

from globals import console
from spackter_util import read_stacks_file
from spackter_util import select_stack

# TODO --long and --format
def list(
    name: Annotated[Optional[str],
        typer.Argument(help=
        """
        TODO
        """)] = "",
    id: Annotated[Optional[bool],
        typer.Option("--id", help=
        """
        ID of spack stack. Needed if two stack with same name exist at different prefixes.
        """
        )] = False,
):
    if not name:
        print_compact_list()
    else:
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
            print("===> Use 'spackter list <id> --id' to specify the intended spack stack.")
            print(f"===> Aborting.")
            raise typer.Exit(code=1)
        else:
            spackter_entry = selected[0][1]
            print_create_summary(spackter_entry)


def print_compact_list(only_name: Optional[str] = None):
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


def print_create_summary(spackter_entry: dict):
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
