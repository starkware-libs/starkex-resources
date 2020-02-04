FROM python:3.7
RUN apt update && apt -y install netcat && apt clean


# First install the dependencies.
COPY mock_availability_gateway/mock_availability_gateway.egg-info/requires.txt /app/mock_availability_gateway/
RUN pip3 install -r /app/mock_availability_gateway/requires.txt

COPY starkware_storage-0.1.zip /app/storage/
RUN pip3 install /app/storage/starkware_storage-0.1.zip
COPY mock_availability_gateway/stark_ex_objects-0.1.zip /app/stark_ex_objects/
RUN pip3 install /app/stark_ex_objects/stark_ex_objects-0.1.zip

COPY mock_availability_gateway/mock_availability_gateway-0.1.zip /app/mock_availability_gateway/
RUN pip3 install /app/mock_availability_gateway/mock_availability_gateway-0.1.zip

COPY mock_availability_gateway/config.yml /

CMD ["python3", "-u", "-m", "mock_availability_gateway.mock_availability_gateway"]
