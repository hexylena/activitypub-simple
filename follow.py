#!/usr/bin/env python
import apcrypt
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('actor')
parser.add_argument('target_id')
parser.add_argument('--unfollow', action='store_true', help='Unfollow the target')
parser.add_argument('--dry', action='store_true', help='Do not actually send')
args = parser.parse_args()

recipient_url = args.target_id
recipient_inbox = args.target_id + "/inbox"

sender_url = f"https://ap.galaxians.org/users/{args.actor}"
sender_key = f"https://ap.galaxians.org/users/{args.actor}#main-key"
activity_id = f"https://ap.galaxians.org/users/{args.actor}/follows/test"

follow_request_message = {
    "@context": "https://www.w3.org/ns/activitystreams",
    "id": sender_url + '#follow',
    "type": "Follow",
    "actor": sender_url,
    "object": recipient_url
}
if args.unfollow:
    follow_request_message['id'] += '#undo'
    follow_request_message['type'] = 'Undo'
    follow_request_message['object'] = {
        'id': 'https://mastodon.social/316e86fa-d8b8-4ab1-a306-29aab8b75b64',
        'type': 'Follow',
        'actor': sender_url, # 'https://mastodon.social/users/hexylena',
        'object': recipient_url, 
    }

headers = apcrypt.generate_signed_headers('private.pem', follow_request_message, recipient_inbox, sender_key)
print(headers)
print(follow_request_message)

if not args.dry:
    r = requests.post(recipient_inbox, headers=headers, json=follow_request_message)
    print(r.headers)
    print(r.text)
    print(r.status_code)

    STATE = load_state()
    STATE[args.actor]['following'].append(args.target_id)
    STATE[args.actor]['following'] = list(set(STATE[args.actor]['following']))
    save_state(STATE)


    # If they approve, we'll get back
    # {'@context': 'https://www.w3.org/ns/activitystreams', 'id': 'https://mastodon.social/users/hexylena#accepts/follows/', 'type': 'Accept', 'actor': 'https://mastodon.social/users/hexylena', 'object': {'id': 'https://ap.galaxians.org/users/alice#follow', 'type': 'Follow', 'actor': 'https://ap.galaxians.org/users/alice', 'object': 'https://mastodon.social/users/hexylena'}}
    # Or "type": "Deny" if they dent,
    # Or nothing if we're in LIMBO.
