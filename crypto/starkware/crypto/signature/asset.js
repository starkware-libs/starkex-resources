/////////////////////////////////////////////////////////////////////////////////
// Copyright 2019 StarkWare Industries Ltd.                                    //
//                                                                             //
// Licensed under the Apache License, Version 2.0 (the "License").             //
// You may not use this file except in compliance with the License.            //
// You may obtain a copy of the License at                                     //
//                                                                             //
// https://www.starkware.co/open-source-license/                               //
//                                                                             //
// Unless required by applicable law or agreed to in writing,                  //
// software distributed under the License is distributed on an "AS IS" BASIS,  //
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.    //
// See the License for the specific language governing permissions             //
// and limitations under the License.                                          //
/////////////////////////////////////////////////////////////////////////////////

const BN = require('bn.js');
const encUtils = require('enc-utils');
const sha3 = require('js-sha3');
const assert = require('assert');


// Generate BN of 1.
const oneBn = new BN('1', 16);

// This number is used to shift the packed encoded asset information by 256 bits.
const shiftBN = new BN('10000000000000000000000000000000000000000000000000000000000000000', 16);

// Used to mask the 251 least signifcant bits given by Keccack256 to produce the final asset ID.
const mask = new BN('3ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff', 16);


/*
 Computes the hash representing the asset ID for a given asset.
 asset is a dictionary containing the type and data of the asset to parse. the asset type is
 represented by a string describing the associated asset while the data is a dictionary
 containing further infomartion to distinguish between assets of a given type (such as the
 address of the smart contract of an ERC20 asset).
 The function returns the computed asset ID as a hex-string.

 For example:

    assetDict = {
        type: 'ERC20',
        data: { quantum: '10000', tokenAddress: '0xdAC17F958D2ee523a2206206994597C13D831ec7' }
    }

 Will produce an the following asset ID:

    '0x352386d5b7c781d47ecd404765307d74edc4d43b0490b8e03c71ac7a7429653'.
*/
function getAssetType(assetDict) {
    const assetSelector = getAssetSelector(assetDict.type);

    // Expected length is maintained to fix the length of the resulting asset info string in case of
    // leading zeroes (which might be omitted by the BN object).
    let expectedLen = encUtils.removeHexPrefix(assetSelector).length;

    // The asset info hex string is a packed message containing the hexadecimal representation of
    // the asset data.
    let assetInfo = new BN(encUtils.removeHexPrefix(assetSelector), 16);

    if (assetDict.data.tokenAddress !== undefined) {
        // In the case there is a valid tokenAddress in the data, we append that to the asset info
        // (before the quantum).
        const tokenAddress = new BN(encUtils.removeHexPrefix(assetDict.data.tokenAddress), 16);
        assetInfo = assetInfo.mul(shiftBN);
        expectedLen += 64;
        assetInfo = assetInfo.add(tokenAddress);
    }

    // Default quantum is 1 (for assets which don't specify quantum explicitly).
    const quantInfo = assetDict.data.quantum;
    const quantum = (quantInfo === undefined) ? oneBn : new BN(quantInfo, 10);
    assetInfo = assetInfo.mul(shiftBN);
    expectedLen += 64;
    assetInfo = assetInfo.add(quantum);

    let assetType = sha3.keccak_256(
        encUtils.hexToBuffer(addLeadingZeroes(assetInfo.toJSON(), expectedLen))
    );
    assetType = new BN(assetType, 16);
    assetType = assetType.and(mask);

    return '0x' + assetType.toJSON();
}

function getAssetId(assetDict) {
    const assetType = new BN(encUtils.removeHexPrefix(getAssetType(assetDict)), 16);
    // For ETH and ERC20, the asset ID is simply the asset type.
    let assetId = assetType;
    if (assetDict.type === 'ERC721') {
        // ERC721 assets require a slightly different construction for asset info.
        let assetInfo = new BN(encUtils.utf8ToBuffer('NFT:'), 16);
        assetInfo = assetInfo.mul(shiftBN);
        assetInfo = assetInfo.add(assetType);
        assetInfo = assetInfo.mul(shiftBN);
        assetInfo = assetInfo.add(new BN(parseInt(assetDict.data.tokenId), 16));
        const expectedLen = 136;
        assetId = sha3.keccak_256(
            encUtils.hexToBuffer(addLeadingZeroes(assetInfo.toJSON(), expectedLen))
        );
        assetId = new BN(assetId, 16);
        assetId = assetId.and(mask);
    }

    return '0x' + assetId.toJSON();
}

/*
 Computes the given asset's unique selector based on its type.
*/
function getAssetSelector(assetDictType) {
    let seed = '';
    switch (assetDictType.toUpperCase()) {
        case 'ETH':
            seed = 'ETH()';
            break;
        case 'ERC20':
            seed = 'ERC20Token(address)';
            break;
        case 'ERC721':
            seed = 'ERC721Token(address,uint256)';
            break;
        default:
            throw new Error(`Unknown token type: ${assetDictType}`);
    }
    return encUtils.sanitizeHex(sha3.keccak_256(seed).slice(0, 8));
}

/*
 Adds leading zeroes to the input hex-string to complement the expected length.
*/
function addLeadingZeroes(hexStr, expectedLen) {
    let res = hexStr;
    assert(res.length <= expectedLen);
    while (res.length < expectedLen) {
        res = '0' + res;
    }
    return res;
}

module.exports = {
    getAssetType,
    getAssetId  // Function.
};
