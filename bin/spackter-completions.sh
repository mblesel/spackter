#!/usr/bin/env bash

# Heavily influenced by: https://tylerthrailkill.com/2019-01-19/writing-bash-completion-script-with-subcommands/

# _spackter_completions() {
#     if [[ "${#COMP_WORDS[@]}" != "2" ]]; then
#         return
#     fi
#
#     COMPREPLY=($(compgen -W "load list create add delete " "${COMP_WORDS[1]}"))
# }
#
# complete -F _spackter_completions spackter


_spackter() {
  local i=1 cmd

  # find the subcommand
  while [[ "$i" -lt "$COMP_CWORD" ]]
  do
    local s="${COMP_WORDS[i]}"
    case "$s" in
      -*) ;;
      *)
        cmd="$s"
        break
        ;;
    esac
    (( i++ ))
  done

  if [[ "$i" -eq "$COMP_CWORD" ]]
  then
    local cur="${COMP_WORDS[COMP_CWORD]}"
    COMPREPLY=($(compgen -W "add create delete list load --help --version" -- "$cur"))
    return # return early if we're still completing the 'current' command
  fi

  # we've completed the 'current' command and now need to call the next completion function
  # subcommands have their own completion functions
  case "$cmd" in
    add) _spackter_add ;;
    create) _spackter_create ;;
    delete) _spackter_delete ;;
    list) _spackter_list ;;
    load) _spackter_load ;;
    *)          ;;
  esac
}

_spackter_add ()
{
  local i=1 subcommand_index

  # find the subcommand
  while [[ $i -lt $COMP_CWORD ]]; do
    local s="${COMP_WORDS[i]}"
    case "$s" in
    add)
      subcommand_index=$i
      break
      ;;
    esac
    (( i++ ))
  done

  while [[ $subcommand_index -lt $COMP_CWORD ]]; do
    local s="${COMP_WORDS[subcommand_index]}"
    case "$s" in
      plain)
        _main_subcommand_plain 
        return
        ;;
      help) 
        COMPREPLY=""
        return
        ;;
    esac
    (( subcommand_index++ ))
  done

  local cur="${COMP_WORDS[COMP_CWORD]}"
  compopt -o default
  COMPREPLY=($(compgen -W "--help --env-script=" -- "$cur"))
}

_spackter_create ()
{
  local i=1 subcommand_index

  # find the subcommand
  while [[ $i -lt $COMP_CWORD ]]; do
    local s="${COMP_WORDS[i]}"
    case "$s" in
    create)
      subcommand_index=$i
      break
      ;;
    esac
    (( i++ ))
  done

  while [[ $subcommand_index -lt $COMP_CWORD ]]; do
    local s="${COMP_WORDS[subcommand_index]}"
    case "$s" in
      plain)
        _main_subcommand_plain 
        return
        ;;
      help) 
        COMPREPLY=""
        return
        ;;
    esac
    (( subcommand_index++ ))
  done

  local cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=($(compgen -W "--configs= --prefix= --compiler= --allow-errors= --no-allow-errors= --create-mirror= --with-mirror= --spack_branch= --spack_commit= --help" -- "$cur"))
} 

_spackter_delete ()
{
  local i=1 subcommand_index

  # find the subcommand
  while [[ $i -lt $COMP_CWORD ]]; do
    local s="${COMP_WORDS[i]}"
    case "$s" in
    delete)
      subcommand_index=$i
      break
      ;;
    esac
    (( i++ ))
  done

  while [[ $subcommand_index -lt $COMP_CWORD ]]; do
    local s="${COMP_WORDS[subcommand_index]}"
    case "$s" in
      plain)
        _main_subcommand_plain 
        return
        ;;
      help) 
        COMPREPLY=""
        return
        ;;
    esac
    (( subcommand_index++ ))
  done

  local cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=($(compgen -W "--id --only-spackter-entry --help" -- "$cur"))
} 

_spackter_list ()
{
  local i=1 subcommand_index

  # find the subcommand
  while [[ $i -lt $COMP_CWORD ]]; do
    local s="${COMP_WORDS[i]}"
    case "$s" in
    list)
      subcommand_index=$i
      break
      ;;
    esac
    (( i++ ))
  done

  while [[ $subcommand_index -lt $COMP_CWORD ]]; do
    local s="${COMP_WORDS[subcommand_index]}"
    case "$s" in
      plain)
        _main_subcommand_plain 
        return
        ;;
      help) 
        COMPREPLY=""
        return
        ;;
    esac
    (( subcommand_index++ ))
  done

  local cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=($(compgen -W "--id --help" -- "$cur"))
} 


_spackter_load ()
{
  local i=1 subcommand_index

  # find the subcommand
  while [[ $i -lt $COMP_CWORD ]]; do
    local s="${COMP_WORDS[i]}"
    case "$s" in
    load)
      subcommand_index=$i
      break
      ;;
    esac
    (( i++ ))
  done

  while [[ $subcommand_index -lt $COMP_CWORD ]]; do
    local s="${COMP_WORDS[subcommand_index]}"
    case "$s" in
      plain)
        _main_subcommand_plain 
        return
        ;;
    esac
    (( subcommand_index++ ))
  done

  local cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=($(compgen -W "--id --only-env-script --help" -- "$cur"))
} 


complete -o bashdefault -F _spackter spackter
