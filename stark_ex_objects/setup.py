from os import path

from setuptools import find_packages, setup

# Reads the contents of your README file.
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='stark_ex_objects',
    version='0.1',
    url='https://starkware.co',
    packages=find_packages(),
    namespace_packages=['starkware'],
    install_requires=[
        'marshmallow-dataclass==7.1.0',
        'marshmallow==3.2.1'
    ],
)
