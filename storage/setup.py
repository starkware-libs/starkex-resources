from os import path

from setuptools import find_packages, setup

# Reads the contents of your README file.
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='starkware_storage',
    version='0.1',
    author='StarkWare Industries',
    author_email='info@starkware.co',
    url='https://starkware.co',
    packages=find_packages(),
    namespace_packages=['starkware'],
    install_requires=[
        'aerospike==3.9.0',
        'aiobotocore==0.11.0',
        'aioredis==1.2.0',
        'aioredlock==0.3.0',
        'cachetools==3.1.1',
    ],
    long_description=long_description,
)
