from cryptography.hazmat.backends import default_backend as crypto_default_backend
import uuid
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

parser = argparse.ArgumentParser()
parser.add_argument('actor')
parser.add_argument('content')
args = parser.parse_args()

#target_id = "https://mastodon.social/users/hexylena"

sender_url = f"https://ap.galaxians.org/users/{args.actor}"
sender_key = f"https://ap.galaxians.org/users/{args.actor}#main-key"
activity_id = f"https://ap.galaxians.org/users/{args.actor}/follows/test"

# The following is to sign the HTTP request as defined in HTTP Signatures.
private_key_text = open('private.pem', 'r').read() # load from file

private_key = crypto_serialization.load_pem_private_key(
    private_key_text.encode('utf-8'),
    password=None,
    backend=crypto_default_backend()
)

current_date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

recipient_inbox = "https://mastodon.social/inbox"
recipient_parsed = urlparse(recipient_inbox)
recipient_host = recipient_parsed.netloc
recipient_path = recipient_parsed.path

# Now that the header is set up, we will construct the message

now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
id = str(uuid.uuid4())

# Generate the toot and save it.
STATE = load_state()
text = args.content
STATE[args.actor]['toots'].append({
    'date': now,
    'id': id,
    'text': text,
    'replies': [],
})
save_state(STATE)


toot = {
    '@context': ['https://www.w3.org/ns/activitystreams', {'ostatus': 'http://ostatus.org#', 'atomUri': 'ostatus:atomUri', 'inReplyToAtomUri': 'ostatus:inReplyToAtomUri', 'conversation': 'ostatus:conversation', 'sensitive': 'as:sensitive', 'toot': 'http://joinmastodon.org/ns#', 'votersCount': 'toot:votersCount'}],
    'id': f'{sender_url}/statuses/{id}/activity',
    'type': 'Create',
    'actor': sender_url,
    'published': now,
    'to': ['https://www.w3.org/ns/activitystreams#Public'],
    'cc': [f'{sender_url}/followers'],
    'object': {
        'id': f'{sender_url}/statuses/{id}',
        'type': 'Note',
        'summary': None,
        'inReplyTo': None,
        'published': now,
        'url': 'https://ap.galaxians.org/@{actor}/{id}',
        'attributedTo': f'{sender_url}',
        'to': ['https://www.w3.org/ns/activitystreams#Public'],
        'cc': [f'{sender_url}/followers'],
        'sensitive': False,
        'atomUri': f'{sender_url}/statuses/{id}',
        'inReplyToAtomUri': None,
        'conversation': 'tag:ap.galaxians.org,2022-11-08:objectId=327749007:objectType=Conversation',
        'content': '<p>{text}</p>',
        'contentMap': {'en': '<p>{text}</p>'},
        'attachment': [],
        'tag': [],
        'replies': {
            'id': f'{sender_url}/statuses/{id}/replies',
            'type': 'Collection',
            'first': {
                'type': 'CollectionPage',
                'next': f'{sender_url}/statuses/{id}/replies?only_other_accounts=true&page=true',
                'partOf': f'{sender_url}/statuses/{id}/replies',
                'items': []
            }
        }
    },
    #'signature': {'type': 'RsaSignature2017', 'creator': f'{sender_key}', 'created': '{now}', 'signatureValue': 'TODO'}
}

import linked_data_sig

linked_data_sig.generate_json_signature(toot, private_key_pem=private_key_text)

# generating digest
request_message_json = json.dumps(toot)
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


print(headers)
print(toot)
r = requests.post(recipient_inbox, headers=headers, json=toot)
print(r.status_code)
print(r.headers)
print(r.text)
