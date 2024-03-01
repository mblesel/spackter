#!/bin/bash

export SPACKTER_ROOT=$(readlink -f $(dirname ${BASH_SOURCE[0]}))
export PATH=${SPACKTER_ROOT}/bin:${PATH}
PYTHON_BIN=$SPACKTER_ROOT/.venv/bin/python

spackter-load () {
    local out=$(spackter load "$@")
    local env_path=$(echo $out | grep -o '/[^ ]*' | awk 'END{print}')
    if [[ -z "$env_path" ]]; then
        echo $out | sed 's/===>/~===>/2g' | tr -s '~' '\n'
    else
        echo $out | sed 's/===>/~===>/2g' | tr -s '~' '\n'
        . $env_path
    fi
}
