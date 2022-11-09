from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from lib import load_state, save_state

from urllib.parse import urlparse
import base64
import datetime
import requests
import json
import hashlib
import argparse


def generate_signed_headers(private_key, message, recipient_url, sender_key):
    # The following is to sign the HTTP request as defined in HTTP Signatures.
    with open(private_key, 'r') as handle:
        private_key_text = handle.read() # load from file

    private_key = crypto_serialization.load_pem_private_key(
        private_key_text.encode('utf-8'),
        password=None,
        backend=crypto_default_backend()
    )
    current_date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

    recipient_parsed = urlparse(recipient_url)
    recipient_host = recipient_parsed.netloc
    recipient_path = recipient_parsed.path

    # generating digest
    request_message_json = json.dumps(message)
    digest = base64.b64encode(hashlib.sha256(request_message_json.__str__().encode('utf-8')).digest())

    signature_text = b'(request-target): post %s\ndigest: SHA-256=%s\nhost: %s\ndate: %s' % (recipient_path.encode('utf-8'), digest, recipient_host.encode('utf-8'), current_date.encode('utf-8'))

    raw_signature = private_key.sign(
        signature_text,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    signature_header = 'keyId="%s",algorithm="rsa-sha256",headers="(request-target) digest host date",signature="%s"' % (sender_key, base64.b64encode(raw_signature).decode('utf-8'))

    headers = {
        'Date': current_date,
        'Content-Type': 'application/activity+json',
        'Host': recipient_host,
        'Digest': "SHA-256="+digest.decode('utf-8'),
        'Signature': signature_header
    }
    return headers
