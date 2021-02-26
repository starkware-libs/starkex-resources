from os import path

from setuptools import find_packages, setup

# Reads the contents of your README file.
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mock_availability_gateway',
    version='0.1',
    author='StarkWare Industries',
    author_email='info@starkware.co',
    url='https://starkware.co',
    packages=find_packages(),
    install_requires=[
        'aiohttp==3.7.4',
        'PyYAML==5.1',
        'Web3==5.2.2',
    ],
    package_data={
        '': ['data.json']
    },
    long_description=long_description,
)
