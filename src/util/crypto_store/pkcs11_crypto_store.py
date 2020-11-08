import os
from typing import Tuple

import pkcs11
from ethereum.utils import ecrecover_to_pub
from pkcs11.util import ec
from pkcs11.util.ec import encode_ec_public_key
from Crypto.Hash import keccak

# ''
from src.util.crypto_store.crypto_manager import CryptoManagerBase


class Pkcs11CryptoStore(CryptoManagerBase):
    def __init__(self, token, user_pin, label: str = ''):
        lib = pkcs11.lib(os.getenv('PKCS11_MODULE'))
        try:
            self.token = lib.get_token(token_label=token)
        except pkcs11.MultipleTokensReturned:
            raise RuntimeError("Multiple tokens returned for token label")

        self.user_pin = user_pin
        self.label = label or "bridge_key"
        self._address = None
        self.public_key = None

        if self.label:
            self._load_key()

    def _load_key(self):
        with self.token.open(user_pin=self.user_pin) as session:
            keys = session.get_objects({pkcs11.Attribute.CLASS: pkcs11.ObjectClass.PUBLIC_KEY})
            for key in keys:
                if key.label == self.label:
                    self.public_key = encode_ec_public_key(key)[24:]
                    self._address = self._address_from_pub(key)

    def generate(self):
        if not self._address:
            # if we got here, we didn't succeed in loading during _load_key, so we can just generate a new one without
            # being afraid of multiple objects
            # todo: handle multiple objects a little more gracefully? We'll see how other HSMs handle this shit...
            with self.token.open(rw=True, user_pin=self.user_pin) as session:
                ecparams = session.create_domain_parameters(
                    pkcs11.KeyType.EC, {
                        pkcs11.Attribute.EC_PARAMS: ec.encode_named_curve_parameters('secp256k1'),
                    }, local=True)

                pub, priv = ecparams.generate_keypair(label=self.label, store=True)
                self._address = self._address_from_pub(pub)
                self.public_key = encode_ec_public_key(pub)[24:]
        return self.label

    @property
    def address(self) -> str:
        return self._address

    def sign(self, tx_hash: str) -> Tuple[int, int, int]:

        msg_bytes = bytes.fromhex(tx_hash)

        v, r, s = 0, 0, 0

        with self.token.open(user_pin=self.user_pin) as session:
            priv = session.get_key(key_type=pkcs11.KeyType.EC,
                                   object_class=pkcs11.ObjectClass.PRIVATE_KEY,
                                   label=self.label)
            signature = priv.sign(msg_bytes, mechanism=pkcs11.Mechanism.ECDSA)

            r = int.from_bytes(signature[0:32], byteorder='big')
            s = int.from_bytes(signature[32:], byteorder='big')

            secpk1n = 115792089237316195423570985008687907852837564279074904382605163141518161494337
            s = s if s * 2 < secpk1n else secpk1n - s

            v = 0

            for _v in range(27, 29):
                pub2 = ecrecover_to_pub(msg_bytes, _v, r, s)
                if pub2 == self.public_key:
                    v = _v

            if not v:
                raise ValueError("Failed to sign")

        return r, s, v
        # unpack

    @staticmethod
    def _address_from_pub(pubkey: bytes):
        public_der = encode_ec_public_key(pubkey)

        # public key in der encoding is 32 bytes of header stuff, then 65 bytes of the uncompressed public key
        # so we start from the 33rd byte
        pub_uncompressed = public_der[24:].hex()
        return pubkey_to_addr(pub_uncompressed)


def pubkey_to_addr(pubkey: str) -> str:
    pub_int = int(pubkey, 16)
    keccak_hash = keccak.new(digest_bits=256)
    keccak_hash.update(pub_int.to_bytes(64, 'big'))
    addr = keccak_hash.hexdigest()
    addr = '0x' + addr[-40:]
    return addr


def run():
    store = Pkcs11CryptoStore(token="token", user_pin="1234", key_id=b'&\xb7&\xa4\xd9y?\xdab\xf4')

    store.generate()

    print(store.address)
    print(store.key_id)
    # lib = pkcs11.lib('/usr/local/lib/softhsm/libsofthsm2.so')
    # token = lib.get_token(token_label='token')
    #
    # data = b'INPUT DATA'
    # mylabel = "bridge2"
    # done = False
    # # Open a session on our token
    # with token.open(rw=True, user_pin='1234') as session:
    #     # Generate an EC keypair in this session from a named curve
    #     ecparams = session.create_domain_parameters(
    #         pkcs11.KeyType.EC, {
    #             pkcs11.Attribute.EC_PARAMS: ec.encode_named_curve_parameters('secp256k1'),
    #         }, local=True)
    #
    #     keys = session.get_objects({pkcs11.Attribute.CLASS: pkcs11.ObjectClass.PUBLIC_KEY})
    #     for key in keys:
    #         if key.label == mylabel:
    #             pubk = encode_ec_public_key(key)
    #             print(pubk.hex())
    #             done = True
    #
    #     if done:
    #         return
    #
    #     pub, priv = ecparams.generate_keypair(label=mylabel, mechanism=pkcs11.Mechanism.ECDSA, store=True)
    #
    #
    #
    #     # Sign
    #     signature = priv.sign(data, mechanism=pkcs11.Mechanism.ECDSA)
    #     print(signature)
    #
    #     # pub = session.get_key(key_type=pkcs11.KeyType.EC,
    #     #                       object_class=pkcs11.ObjectClass.PUBLIC_KEY)
    #     # key = pkcs11.load_public_key(encode_ec_public_key(pub))
    #     pubk = encode_ec_public_key(pub)
    #     print(pubk.hex())


if __name__ == '__main__':
    run()
