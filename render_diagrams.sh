#!/usr/bin/env bash

DRAWIO='/Applications/draw.io.app/Contents/MacOS/draw.io'
DIR='state_diagrams'

find "./${DIR}" -type f -exec basename {} \; |\
  cut -d '.' -f1 |\
  xargs -I % bash -c "${DRAWIO} -x -o ${DIR}/renders/%.png ${DIR}/%.drawio"
