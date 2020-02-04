python_package(mock_availability_gateway mock_availability_gateway
    mock_availability_gateway/__init__.py
    mock_availability_gateway/data.json
    mock_availability_gateway/mock_availability_gateway.py
    README.md
    setup.py
)

# Copy Dockerfile.
copy_files_target(mock_availability_gateway_docker
    config.yml
    Dockerfile
)

python_dependency(mock_availability_gateway_docker stark_ex_objects)
python_dependency(mock_availability_gateway_docker mock_availability_gateway)

add_dependencies(mock_availability_gateway_docker stark_ex_objects)
add_dependencies(mock_availability_gateway_docker mock_availability_gateway)
