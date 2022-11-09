#!/usr/bin/env python
import requests 
import json
import apcrypt
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('actor')
parser.add_argument('target_id')
parser.add_argument('--unfollow', action='store_true', help='Unfollow the target')
parser.add_argument('--dry', action='store_true', help='Do not actually send')
args = parser.parse_args()


response = {
    '@context': 'https://www.w3.org/ns/activitystreams',
    'id': f'https://ap.galaxians.org/users/{args.actor}#accepts/follows/',
    'type': 'Accept',
    'actor': f'https://ap.galaxians.org/users/{args.actor}',
    'object': {
        'id': f"{args.target_id}#follow",
        'type': 'Follow',
        'actor': args.target_id,
        'object': f'https://ap.galaxians.org/users/{args.actor}'
    }
}
sender_url = f"https://ap.galaxians.org/users/{args.actor}"
recipient_inbox = f"{args.target_id}/inbox"
sender_key = f"{sender_url}#main-key"
headers = apcrypt.generate_signed_headers('private.pem', response, recipient_inbox, sender_key)
print(json.dumps(headers, indent=2))
print(json.dumps(response, indent=2))
if not args.dry:
    r = requests.post(recipient_inbox, headers=headers, json=response)
    print(r.headers)
    print(r.text)
    print(r.status_code)
