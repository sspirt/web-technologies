from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
import hashlib
import os

class CryptoManager:
    def __init__(self, password: str, algorithm: str = "chacha20"):
        if not password:
            raise ValueError("Password must not be empty")
        if algorithm.lower() != "chacha20":
            raise ValueError("Only chacha20 is supported")
        self._key = hashlib.sha256(password.encode()).digest()

    def encrypt(self, text: str) -> str:
        nonce = os.urandom(16)
        cipher = Cipher(algorithms.ChaCha20(self._key, nonce), mode=None)
        enc = cipher.encryptor()
        encrypted = enc.update(text.encode())
        return (nonce + encrypted).hex()

    def decrypt(self, encrypted_text: str) -> str:
        try:
            data = bytes.fromhex(encrypted_text)
            nonce, ciphertext = data[:16], data[16:]
            cipher = Cipher(algorithms.ChaCha20(self._key, nonce), mode=None)
            dec = cipher.decryptor()
            return dec.update(ciphertext).decode()
        except Exception:
            raise ValueError("Could not decrypt data")

if __name__ == "__main__":
    manager = CryptoManager("my-password")
    encrypted = manager.encrypt("Hello, Python OOP!")
    print("Encrypted:", encrypted)
    print("Decrypted:", manager.decrypt(encrypted))