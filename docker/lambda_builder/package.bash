#!/bin/bash

OUTPUT_FILE="${1}"
shift
cd /usr/src/app || exit

rm -rf /usr/src/deps/
mkdir -p /usr/src/deps/
if [[ ! -f /usr/src/shared_deps/built ]] ; then
  while [[ ! -z "${1}" ]] ; do
    pip -q install "${1}" -t /usr/src/shared_deps/
    shift
  done
  touch /usr/src/shared_deps/built
fi
cp -pr /usr/src/shared_deps/* /usr/src/deps/

pip -q install -r requirements.txt -t /usr/src/deps/


cd /usr/src/deps || exit
zip -q -r "/usr/src/app/${OUTPUT_FILE}.zip" .
cd /usr/src/app || exit
if [[ -f "./exclude.lst" ]]; then
    zip -q -r "/usr/src/app/${OUTPUT_FILE}.zip" . -x @/exclude.lst -x @./exclude.lst
else
    zip -q -r "/usr/src/app/${OUTPUT_FILE}.zip" . -x @/exclude.lst
fi
