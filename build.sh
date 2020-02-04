#!/bin/bash
set -e

if [ $# -lt 1 ]
then
    FLAVOR="Release"
else
    FLAVOR=$1
fi

mkdir -p build/$FLAVOR
(cd build/$FLAVOR; cmake -DCMAKE_BUILD_TYPE=$FLAVOR ../..)
make -C build/$FLAVOR
