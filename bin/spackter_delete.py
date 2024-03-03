import typer
import shutil
from pathlib import Path
from typing_extensions import Annotated
from typing import Optional

from spackter_util import select_stack
from spackter_util import remove_stack
from spackter_list import print_compact_list



# TODO --yes-to-all?
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
        stack = selected[0][1]
        spack_root = Path(selected[0][0])
        if not only_spackter_entry and spack_root.exists():
            if typer.confirm(f"===> Delete '{spack_root}' from disk?"):
                shutil.rmtree(spack_root)
                print(f"===> '{spack_root}' deleted.")
        print(f"===> Removing '{stack['name']}' from spackter database.")
        remove_stack(spack_root)
