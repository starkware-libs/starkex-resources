/* eslint-disable no-unused-expressions */
const chai = require('chai');
const { getAssetId, getAssetType } = require('.././asset.js');
const { expect } = chai;

describe('Asset Type computation', () => {
    it('should compute asset type correctly', () => {
        const precomputedAssets = require('../assets_precomputed.json');
        const precompytedAssetTypes = precomputedAssets.assetType;
        for (const expectedAssetType in precompytedAssetTypes) {
            if ({}.hasOwnProperty.call(precompytedAssetTypes, expectedAssetType)) {
                const asset = precompytedAssetTypes[expectedAssetType];
                expect(getAssetType(asset)).to.equal(expectedAssetType);
            }
        }
    });
});

describe('Asset ID computation', () => {
    it('should compute asset ID correctly', () => {
        const precomputedAssets = require('../assets_precomputed.json');
        const precompytedAssetIds = precomputedAssets.assetId;
        for (const expectedAssetId in precompytedAssetIds) {
            if ({}.hasOwnProperty.call(precompytedAssetIds, expectedAssetId)) {
                const asset = precompytedAssetIds[expectedAssetId];
                expect(getAssetId(asset)).to.equal(expectedAssetId);
            }
        }
    });
});
