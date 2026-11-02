import logging

logger = logging.getLogger("StreamVault.Crypto")

def apply_crypto_patch():
    """
    Patches Hydrogram's AES IGE encryption/decryption with cryptg (C/Rust-optimized).
    This speeds up file transfers and streaming by 1,000x - 10,000x compared to pure Python pyaes,
    preventing Telegram MTProto 'upload.GetFile Request timed out' errors.
    """
    try:
        import cryptg
        import hydrogram.crypto.aes as aes
        
        aes.ige256_encrypt = cryptg.encrypt_ige
        aes.ige256_decrypt = cryptg.decrypt_ige
        logger.info("High-speed MTProto AES acceleration enabled via cryptg (hardware-accelerated)!")
        return True
    except ImportError:
        logger.warning("cryptg not installed; Hydrogram running on default pure-Python crypto.")
        return False
    except Exception as e:
        logger.warning(f"Could not apply crypto patch: {e}")
        return False
