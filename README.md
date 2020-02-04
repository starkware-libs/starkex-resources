# Stark Exchange Resources

This repo hold a collection of tools to support the Stark Exchange.
The Stark Exchange is a STARK-powered scalability engine for crypto exchanges.
It uses cryptographic proofs to attest to the validity of a batch of transactions (such as trades
and transfers) and updates a commitment to the state of the exchange on-chain.

The Stark Exchange allows exchanges to provide non-custodial trading at scale with high liquidity
and lower costs.

## Modules

1. [committee](committee/README.md) - Reference committee member service implementation
2. [crypto](crypto/README.md) - A cryptographic library for the Stark Exchange
3. [storage](storage/README.md) - A storage abstraction library
4. [stark_ex_objects](stark_ex_objects/README.md) - Various python objects used by the Stark
   Exchange

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
