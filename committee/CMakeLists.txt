python_package(stark_ex_committee committee
    committee/__init__.py
    committee/availability_gateway_client.py
    committee/committee.py
    committee/custom_validation.py
    committee/dump_vaults_tree.py
    setup.py
)

# Copy Dockerfile.
copy_files_target(stark_ex_committee_docker
    Dockerfile
    config.yml
    private_key.txt
)

add_dependencies(stark_ex_committee_docker stark_ex_committee)
add_dependencies(stark_ex_committee_docker stark_ex_objects starkware_crypto starkware_storage)

python_dependency(stark_ex_committee_docker stark_ex_objects)
python_dependency(stark_ex_committee_docker starkware_crypto)
python_dependency(stark_ex_committee_docker starkware_storage)

add_subdirectory(mock_availability_gateway)


# Copy docker-compose.
copy_files_target(committee_test
    docker-compose.yml
)


add_dependencies(committee_test
    mock_availability_gateway_docker
    stark_ex_aerospike
    stark_ex_committee_docker
)
