from typing import Optional
from rich.console import Console
from rich.table import Table

from spackter_util import read_stacks_file

console = Console()

# TODO --long and --format
def list():
    print_compact_list()


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


