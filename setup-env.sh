#!/bin/bash

export SPACKTER_ROOT=$(readlink -f $(dirname ${BASH_SOURCE[0]}))
export PATH=${SPACKTER_ROOT}/bin:${PATH}

