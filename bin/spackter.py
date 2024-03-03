import typer

from typing_extensions import Annotated
from typing import Optional
from rich import print

from globals import __version__

import spackter_list
import spackter_load
import spackter_delete
import spackter_add
import spackter_create


spackter = typer.Typer()


spackter.command(help=
    """
    Add a spack stack that was not created by spackter to the database.
    """
    )(spackter_add.add)


spackter.command(help=
    """
    Deletes a spack stack.
    --only-spackter-entry can be set to only remove the spackter database entry and not delete the spack stack from disk.
    """
    )(spackter_delete.delete)


spackter.command(help=
    """
    Outputs the location of the 'env.sh' script that needs to be sourced to activate 
    the given spack stack.
    """
    )(spackter_load.load)
        

spackter.command(help=
    """
    Lists all currently installed spack stacks.
    """
    )(spackter_list.list)


spackter.command(help=
    """
    Create a new spack stack with a given name.
    'SPACKTER_ROOT/configs' contains directories with spack and spackter 
    configurations files which are used during creation.
    See 'default' and 'test' directories for examples.
    """
    )(spackter_create.create)


def version_callback(value: bool):
    if value:
        print(f"spackter v{__version__}")
        raise typer.Exit()


@spackter.callback(help=
    """
    Spackter is a tool for the creation and management of multiple spack stacks on the same system.
    Creation of new spack stacks can be configured in depth via multiple configuration files.
    Examples can be found at 'SPACKTER_ROOT/configs'.
    """
)
def main(version: Annotated[Optional[bool], typer.Option("--version", callback=version_callback, is_eager=True)] = None):
    pass


if __name__ == "__main__":
    spackter()
