# Spackter

Spackter is a tool for the creation and management of multiple spack stacks on the same system.
Creation of new spack stacks can be configured in depth via multiple configuration files.
Examples can be found at `<SPACKTER_ROOT>/configs`.

## Usage

Source Spackter's `setup-env.sh` script. This puts the `spackter` command in your path and sets required environment variables.
When Spackter is first executed it installs a python virtual environment with all python dependencies.
Spackter requires `python3.7+`  and `git` to be installed on the system.

### Creating new spack stacks

![Spackter create demo](demo/spackter_create.gif)
Spack stacks can be created with the `spackter create` command (see `spackter create --help` for full options).

`spackter create` expects a name for the spack stack as the argument.
The following options are available:

* `--configs=<value>`: where `value` must be the name of one of the directories in the `<SPACKTER_ROOT>/configs/`. By default the `default` configuration is used.
* `--prefix=value`: where `value` is a path to a directory where the spack stack shall be installed. By default all spack stacks get installed to the `<SPACKTER_ROOT>/spack/` directory.
* `--compiler=<value>`: where `value` is a compiler spec in spack syntax (e.g.: `gcc@13.2.0`). This compiler will be built as a first step in the spack stack creation and will be used to compile all packages.
    If this option is omitted spack will use the system compiler for building packages.
* `--allow-errors=<value>`: where `value` is a comma separated string of `['all', 'patch', 'pr', 'package', 'script']`. If a step in one of the listed phases fails Spackter will automatically skip it and proceed with building the spack stack.
* `--no-allow-errors=<value>`: where `value` is a comma separated string of `['all', 'patch', 'pr', 'package', 'script']`. If a step in one of the listed phases fails Spackter will abort. If a phase is not mentioned in this or `--allow-errors`
    the user will be prompted on how to proceed if an error occurs.
* `--create-mirror=<value>`: where `value` is a path to a not yet existing directory. Spackter will create a spack mirror at this path and **only** create a local spack mirror for the given packages.
    With this option no packages are installed, but patches and pull request are already applied and all installation sources will be mirrored locally.
    The spack stack that is initialized here still needs to be installed with the `--with-mirror` option.
    This can be used to have a 2 stage installation, where Spackter first checks if all sources can be fetched by spack.
* `--with-mirror=<value>`: where `value` is a path to an existing spack mirror. Spackter will finish the installation of the given spack stack by using the local mirror.
    This only works if the stack with the given name and prefix has already been initialized with the `--create-mirror` option previously.
* `--spack_branch=<value>`: Spackter will use the given spack branch or tag for stack creation.
* `--spack_commit=<value>`: Spackter will use the given spack commit for stack creation.

#### Spackter configs

Multiple phases of the creation of a spack stack are configured via the files contained in the given config directory.
The config directories can contain the following files:

* **spack configuration files**: If spack configuration files are placed in the config dir they will be copied over to the `etc/spack/` directory of the created spack stack and used by spack.
   Spackter sets `SPACK_DISABLE_LOCAL_CONFIG=1` so that spack's **site** configuration files are always used. If a configuration file is not present or left empty the default spack configuration settings will be used.
* **patches**: if the `<config-dir>/patches` directory contains any `*.patch` files Spackter will try to apply them during spack stack creation.
* **Pull Requests**: The `pull-requests.spackter` file may contain a list of pull request from the official spack Github repository that Spackter will try to apply during stack creation. The syntax is one PR number per line.
* **packages**: The `package-list.spackter` file may contain a list of packages that shall be installed for this spack stack. The syntax is one package per line.
* **post install script**: The `post-install-script.spackter` may contain shell commands that shall be executed at the end of spack stack creation. The script will be executed with the spack stacks root directory as current working directory.
* **pre- and post-script**: The `pre-script.spackter` and `post-script.spackter` files will be used to create a `env.sh` script that will be used to load the spack created spack stack. The pre-script part will be sourced before the `setup-env-sh`
    of the spack stack is sourced and the post-script afterwards. They can for example be used to set environment variables and to automatically load modules each time the spack stack is loaded.

For examples of all of these configurations settings see the `configs/test` directory.

### Listing installed spack stacks

![Spackter list demo](demo/spackter_list.gif)
The `spackter list` command gives a list of all installed spack stacks and some of their most important configuration options.
The given `ID` for each spack stack can be used with the `--id` option of the following commands if there are multiple spack stacks with the same name but at different prefixes.
`spackter list` takes an optional name/id arguments to show more information about a specific spack stack.
The following options are available:

* `--id`: If this option is set the first argument to `spackter list` will be interpreted as an id instead of a name.

### Loading a spack stack

![Spackter load demo](demo/spackter_load.gif)
The `spackter load` command is used to load a spack stack.

`spackter load` expects a name/id as the argument.
The following options are available:

* `--id`: If this option is set the first argument to `spackter load` will be interpreted as an id instead of a name.
* `--only-env-script`: Restricts the output of the command to only the path to the spack stack's `env.sh` script. This can be used for easier loading of the stack inside scripts. (e.g.: `. $(spackter load demo --only-env-script)`.

### Deleting spack stacks

The `spackter delete` command will remove a spack stack.

`spackter delete` expects a name/id as the argument.
The following options are available:

* `--id`: If this option is set the first argument to `spackter delete` will be interpreted as an id instead of a name.
* `--only-spackter-entry`: If this option is set the spack stack will only be removed from the Spackter database and not be deleted from disk.

### Adding external spack stacks

The `spackter add` command will add a spack stack that was not created by Spackter to the database.

`spackter add` expects a name and a path to the root directory of the spack stack as arguments.
The following Options are available:

* `--env-script=<value>`: A path to an env script for this stack which will be sourced when the stack is loaded.
    By default `<SPACK_ROOT>/share/spack/setup-env.sh` is used.
