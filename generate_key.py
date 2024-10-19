import os
import binascii

# Generate a random 24-byte key
secret_key = binascii.hexlify(os.urandom(12)).decode()
print(secret_key)
