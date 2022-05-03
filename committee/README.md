# Committee Service

**A service to validate the data availability for a Stark Exchange**

## Description
The Stark Exchange holds a state of accounts (called vaults) that are updated according to an
ordered series of transactions. It processes transactions in batches of varying sizes, based on size
and time criteria. Following each batch, a Merkle tree is computed over all vaults resulting in
a Merkle root representing the state following the batch which is eventually to be committed
on-chain. Since only the root is committed on-chain, some mechanism is required to guarantee data-availability in case the operator goes rogue.

The Stark Exchange relies on a committee to guarantee data-availability of the off-chain data.
Each committee member is responsible for keeping track of the data associated with
each root and signing an availability claim to attest to the data-availability.

The Stark Exchange operator provides the committee members access to an Availability Gateway.
The Availability Gateway allows the committee members to obtain information about new batches
and to submit signed availability claims.

A batch is uniquely identifiable by its batch_id.
The information about a new batch includes a reference batch_id and a list of (index, value) pairs
with the new values of the vaults that changed relative to the reference batch.
The service combines this information with the data from the reference batch, to compute the new
state and root.
Typically the reference batch is the immediate predecessor of the new batch. However, due to the
nature of the blockchain, it is possible that a batch created by the Stark Exchange is later
reverted and replaced by a different batch.

## Building the Committee Service
The reference committee service implementation can be compiled into a docker image
by running
```
./build.sh
```
and then running
```
docer build -f committee/Dockerfile build/Release
```

## Running the Committee Service
The docker image expects to find a `config.yaml` file in its root directory. This file should be
mounted to the docker at run time.

Service operators are expected to do the following:
The `config.yml` file should be edited to reflect the specific configuration of the Committee Service operator. In particular, this should include the following information:
- `PRIVATE_KEY_PATH` - where the private key for signing availability claims is mounted.
- `CERTIFICATES_PATH` - where the TLS certificates (`user.crt`, `user.key` and `server.crt`) for
  the Availability Gateway are mounted.
- `AVAILABILITY_GW_ENDPOINT` - The address of the Availability Gateway.

A committee member service operator is expected to run a database
and update the STORAGE section of the `config.yml` with the information required to connect to said
database. The reference implementation uses an Aerospike database.

## Publishing Committee Members Data
In the event that the Stark Exchange service malfunctions, becomes non-responsive or even malicious,
users eventually have the option to freeze it. Once frozen, a Committee member should publish the
vault data for the latest root that appears on the on-chain contract.
Exchange users can then use this data to exit the system even without the cooperation of the
Stark Exchange.
To extract this data from the database, a `dump_vaults_tree.py` script is provided herein.

## Security and Privacy Considerations
The Committee Service operator is expected to apply best practices with respect to ensuring the
security of the service which is critical to the operation of the Stark Exchange as well as
best practices for protecting the data it receives contained in the batch updates.

## Copyright
Copyright 2020 StarkWare Industries Ltd.

Licensed under the Apache License, Version 2.0 (the "License").
You may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.starkware.co/open-source-license/

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions
and limitations under the License.
