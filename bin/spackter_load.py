import typer
from typing import Optional
from typing_extensions import Annotated

from spackter_util import select_stack
from spackter_list import print_compact_list

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
    only_env_script: Annotated[Optional[bool],
        typer.Option("--only-env-script", help=
        """
        Only returns path to the 'env.sh' script and does not load the stack for the current session.
        Should be used to load a stack from inside a script.
        """)] = False
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
        if not only_env_script:
            print(f"===> Loading spack stack: {stack['name']} (ID {stack['id']})")
            print(f"===> Using this environment script: {stack['env_script']}")
        else:
            print(f"{stack['env_script']}")
