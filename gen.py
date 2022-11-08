from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend

import os
import sys
if os.path.exists('private.pem'):
    print("Key exists, not overwriting")
    sys.exit(1)

key = rsa.generate_private_key(
    backend=crypto_default_backend(),
    public_exponent=65537,
    key_size=2048
)

private_key = key.private_bytes(
    crypto_serialization.Encoding.PEM,
    crypto_serialization.PrivateFormat.PKCS8,
    crypto_serialization.NoEncryption())

public_key = key.public_key().public_bytes(
    crypto_serialization.Encoding.PEM,
    crypto_serialization.PublicFormat.SubjectPublicKeyInfo
)

with open('private.pem', 'w') as handle:
    handle.write(private_key.decode('utf-8'))

with open('public.pem', 'w') as handle:
    handle.write(public_key.decode('utf-8'))
