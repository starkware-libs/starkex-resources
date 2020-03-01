# How to test

This document describes how to set up and run the tests for the Committee Service.
The point is to avoid "it worked on my machine" scenarios.

# Table of contents
1. [Prerequisites](#prerequisites)
   1. [Build prerequisites](#build-prerequisites)
   1. [Python prerequisites](#python-prerequisites)
   1. [Docker prerequisites](#docker-prerequisites)
   1. [Source code prerequisites](#source-code-prerequisites)
   1. [Testing dependencies](#testing-dependencies)
1. [Build](#build)
1. [Build and test](#build-and-test)

## Prerequisites
* CentOS 7 - (AWS us-east-1 ami-02eac2c0129f6376b)

The below commands will install the listed dependencies on CentOS 7. If you use Ubuntu, or
another different release, take the list and find the commands to get the dependencies.
### Build prerequisites
* cmake3 (from EPEL) (CentOS defaults to v2)
* gcc, c++ compiler, git

Commands that build/install these: (run as root)
```bash
yum install -y epel-release
yum install -y git cmake3 gcc gcc-c++
alternatives --install /usr/local/bin/cmake cmake /usr/bin/cmake3 20 \
--slave /usr/local/bin/ctest ctest /usr/bin/ctest3 \
--slave /usr/local/bin/cpack cpack /usr/bin/cpack3 \
--slave /usr/local/bin/ccmake ccmake /usr/bin/ccmake3 \
--family cmake
```
(Note that this will allow regular users to run the `cmake` command but not the root user.)

### Python prerequisites
* python 3.7 (CentOS defaults to 2.7 and 3.6)

Commands that build/install these: (run as root)
```bash
yum install -y openssl-devel bzip2-devel libffi-devel wget
wget -O /usr/src/Python-3.7.6.tgz https://www.python.org/ftp/python/3.7.6/Python-3.7.6.tgz
tar xzf /usr/src/Python-3.7.6.tgz -C /usr/src
cd /usr/src/Python-3.7.6
./configure --enable-optimizations
make altinstall
alternatives --install /usr/local/bin/python python /usr/local/bin/python3.7m 5 --family python
alternatives --set python /usr/local/bin/python3.7m
```
(Note: as before, this will make Python 3.7.6 default for regular users. Not for root.)

### Docker prerequisites
* Docker (make it available for regular users - the pre v19.03 way)

Commands that build/install these: (run as root)
```bash
yum install -y docker
groupadd docker
gpasswd -a centos docker
systemctl enable docker
systemctl start docker
```
Make sure you exit from the user session and re-login so you get access to docker as the `centos` user.

### Source code prerequisites
* Access to git (probably an SSH key set up)
* Get the source code

Commands that build/install these: (run as a regular user, like `centos`)
```bash
git clone git@github.com:starkware-libs/starkex-resources
cd starkex-resources
```
All future commands will be run from this directory unless otherwise specified.

### Testing dependencies
If you want to run `./presubmit.sh` that also does integration testing and reporting on errors,
you need to install additional dependencies.

* Docker-compose for the container setup
* gmp.h header file for one of the pip3 packages
* Temporarily disable SELinux (for this session only)
* Specific version of `marshmallow-dataclass` Python package (7.1.0)
* New version of NPM (CentOS defaults to a very old version)

Commands that build/install these: (run as root)
```bash
yum install -y gmp-devel docker-compose
pip3 install tox marshmallow-dataclass==7.1.0
setenforce 0
curl -sL https://rpm.nodesource.com/setup_13.x | sudo bash -
yum install -y nodejs
```

## Build
After installing the above dependencies, as a regular user, build with the command:
```bash
./build.sh
```
Optionally, add a 'flavor' input parameter to build into a different directory. (Default flavor is 'Release'.)

## Build and test
After installing the above dependencies (including dependencies for testing), as a regular user (with docker access),
build and test with the command:
```bash
./presubmit.sh
```
Optionally, add a 'flavor' input parameter to use with a different directory. (Default flavor is 'Release'.)
