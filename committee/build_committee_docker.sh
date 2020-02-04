#!/bin/bash
set -e

(cd build/Release; docker build -f committee/Dockerfile .)
