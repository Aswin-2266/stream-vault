import unittest
import os
import tgcrypto

class TestTgCryptoShim(unittest.TestCase):
    def test_ige256_roundtrip(self):
        key = os.urandom(32)
        iv = os.urandom(32)
        plaintext = b"StreamVault MTProto Accelerated Chunk Test 12345" * 10
        # Pad to multiple of 16
        pad_len = 16 - (len(plaintext) % 16)
        plaintext += b"\0" * pad_len

        encrypted = tgcrypto.ige256_encrypt(plaintext, key, iv)
        self.assertNotEqual(plaintext, encrypted)

        decrypted = tgcrypto.ige256_decrypt(encrypted, key, iv)
        self.assertEqual(plaintext, decrypted)

    def test_ctr256_roundtrip(self):
        key = os.urandom(32)
        iv = bytearray(os.urandom(16))
        state = bytearray(1)
        plaintext = b"StreamVault CTR mode verification string" * 5

        encrypted = tgcrypto.ctr256_encrypt(plaintext, key, bytearray(iv), bytearray(state))
        self.assertNotEqual(plaintext, encrypted)

        decrypted = tgcrypto.ctr256_decrypt(encrypted, key, bytearray(iv), bytearray(state))
        self.assertEqual(plaintext, decrypted)

if __name__ == "__main__":
    unittest.main()
