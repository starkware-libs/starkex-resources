FROM python:3.7
RUN apt update && apt -y install netcat python-dev libgmp3-dev && apt clean

# First install the dependencies.
COPY committee/committee.egg-info/requires.txt /app/committee/
RUN pip3 install -r /app/committee/requires.txt
RUN pip install "web3>=5.28,<6"

# Install python packages.
COPY committee/starkware_crypto-0.1.zip /app/starkware-crypto/
RUN pip3 install /app/starkware-crypto/starkware_crypto-0.1.zip
COPY committee/stark_ex_objects-0.1.zip /app/stark_ex_objects/
RUN pip3 install /app/stark_ex_objects/stark_ex_objects-0.1.zip
COPY committee/starkware_storage-0.1.zip /app/storage/
RUN pip3 install /app/storage/starkware_storage-0.1.zip

COPY committee /app/committee
RUN pip3 install /app/committee

CMD ["python3", "-u", "-m", "committee.committee"]
