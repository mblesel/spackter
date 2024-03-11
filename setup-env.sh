#!/bin/bash

export SPACKTER_ROOT=$(readlink -f $(dirname ${BASH_SOURCE[0]}))
# export PATH=${SPACKTER_ROOT}/bin:${PATH}

spackter () {
    # echo $@ | grep -o '\-\-only\-env\-script'
    if [ "$1" = "load" ] && [ -z $(echo $@ | grep -o "\--only-env-script") ] && [ -z $(echo $@ | grep -o "\--help") ] ; then
        local out=$(${SPACKTER_ROOT}/bin/spackter "$@")
        local env_path=$(echo $out | grep -o '/[^ ]*' | awk 'END{print}')
        if [[ -z "$env_path" ]]; then
            echo $out | sed 's/===>/~===>/2g' | tr -s '~' '\n'
        else
            echo $out | sed 's/===>/~===>/2g' | tr -s '~' '\n'
            . $env_path
        fi
    else
        ${SPACKTER_ROOT}/bin/spackter "$@"
    fi
}
