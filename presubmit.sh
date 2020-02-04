#!/bin/bash
set -e

if [ $# -lt 1 ]
then
    FLAVOR="Release"
else
    FLAVOR=$1
fi

./build.sh $FLAVOR
tox -- --junitxml build/reports/$FLAVOR/pytest-starkware-public.xml

# Test JavaScript signature example.
cd crypto/starkware/crypto/signature
npm install
npm run lint
npm run test
