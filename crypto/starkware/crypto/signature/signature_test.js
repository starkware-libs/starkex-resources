const starkwareCrypto = require('./signature.js');
const assert = require('assert');

function testSignature(msg, expectedR, expectedS) {
    const privateKey = '2dccce1da22003777062ee0870e9881b460a8b7eca276870f57c601f182136c';
    const keyPair = starkwareCrypto.ec.keyFromPrivate(privateKey, 'hex');
    const publicKey = starkwareCrypto.ec.keyFromPublic(keyPair.getPublic(true, 'hex'), 'hex');

    const msgSignature = starkwareCrypto.sign(keyPair, msg);
    assert(starkwareCrypto.verify(publicKey, msg, msgSignature));

    const { r, s } = msgSignature;
    assert(r.toString(16) === expectedR);
    assert(s.toString(16) === expectedS);
}

// Msg of length 61.
testSignature(
    'c465dd6b1bbffdb05442eb17f5ca38ad1aa78a6f56bf4415bdee219114a47',
    '5f496f6f210b5810b2711c74c15c05244dad43d18ecbbdbe6ed55584bc3b0a2',
    '4e8657b153787f741a67c0666bad6426c3741b478c8eaa3155196fc571416f3'
);

// Msg of length 61, with leading zeros.
testSignature(
    '00c465dd6b1bbffdb05442eb17f5ca38ad1aa78a6f56bf4415bdee219114a47',
    '5f496f6f210b5810b2711c74c15c05244dad43d18ecbbdbe6ed55584bc3b0a2',
    '4e8657b153787f741a67c0666bad6426c3741b478c8eaa3155196fc571416f3'
);

// Msg of length 62.
testSignature(
    'c465dd6b1bbffdb05442eb17f5ca38ad1aa78a6f56bf4415bdee219114a47a',
    '233b88c4578f0807b4a7480c8076eca5cfefa29980dd8e2af3c46a253490e9c',
    '28b055e825bc507349edfb944740a35c6f22d377443c34742c04e0d82278cf1'
);

// Msg of length 63.
testSignature(
    '7465dd6b1bbffdb05442eb17f5ca38ad1aa78a6f56bf4415bdee219114a47a1',
    'b6bee8010f96a723f6de06b5fa06e820418712439c93850dd4e9bde43ddf',
    '1a3d2bc954ed77e22986f507d68d18115fa543d1901f5b4620db98e2f6efd80'
);
