/* eslint-disable no-unused-expressions */
const chai = require('chai');
const { StarkExEc, getKeyPairFromPath, getAccountPath, grindKey } =
    require('.././key_derivation.js');
const { expect } = chai;

const layer = 'starkex';
const application = 'starkdeployement';

const mnemonic = 'range mountain blast problem vibrant void vivid doctor cluster enough melody ' +
    'salt layer language laptop boat major space monkey unit glimpse pause change vibrant';
const ethAddress = '0xa4864d977b944315389d1765ffa7e66F74ee8cd7';

describe('Key derivation', () => {
    it('should derive key from mnemonic and eth-address correctly', () => {
        let index = 0;
        let path = getAccountPath(layer, application, ethAddress, index);
        let keyPair = getKeyPairFromPath(mnemonic, path);
        expect(keyPair.getPrivate('hex')).to.equal(
            '06cf0a8bf113352eb863157a45c5e5567abb34f8d32cddafd2c22aa803f4892c'
        );

        index = 7;
        path = getAccountPath(layer, application, ethAddress, index);
        keyPair = getKeyPairFromPath(mnemonic, path);
        expect(keyPair.getPrivate('hex')).to.equal(
            '0341751bdc42841da35ab74d13a1372c1f0250617e8a2ef96034d9f46e6847af'
        );

        index = 598;
        path = getAccountPath(layer, application, ethAddress, index);
        keyPair = getKeyPairFromPath(mnemonic, path);
        expect(keyPair.getPrivate('hex')).to.equal(
            '041a4d591a868353d28b7947eb132aa4d00c4a022743689ffd20a3628d6ca28c'
        );
    });
});

describe('Key grinding', () => {
    it('should produce the correct ground key', () => {
        const privateKey = '86F3E7293141F20A8BAFF320E8EE4ACCB9D4A4BF2B4D295E8CEE784DB46E0519';
        expect(grindKey(privateKey, StarkExEc)).to.equal(
            '5c8c8683596c732541a59e03007b2d30dbbbb873556fe65b5fb63c16688f941'
        );
    });
});
