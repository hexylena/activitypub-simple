import os.path
import uuid
import datetime
import yaml
from flask import send_file
import glob
import json
from flask import Flask, Response, request, jsonify
from flask import send_from_directory
import time


app = Flask(__name__)
app.config.from_object(__name__)

STATE = {}

def load_state():
    with open('state.yaml', 'r') as handle:
        return yaml.safe_load(handle)

def save_state(state):
    with open('state.yaml', 'w') as handle:
        yaml.dump(state, handle)

STATE = load_state()
print(STATE)

PUBKEY = open('public.pem', 'r').read().strip()

# Synthetic auto-generated users for test.
def get_user(user):
    if user in STATE:
        return STATE[user]
    else:
        return {
            'name': f'Bot {user}',
            "type": "Service",
            'following': [
                'https://ap.galaxians.org/users/alice',
                'https://mastodon.social/users/hexylena',
                'https://tech.lgbt/users/hexylena',
            ],
        }


def toot_from_state(user, id):
    toot = [x for x in STATE[user]['toots'] if x['id'] == id][0]
    now = toot['date']
    text = toot['text']

    return {
      "id": f"https://ap.galaxians.org/users/{user}/statuses/{id}/activity",
      "type": "Create",
      "actor": f"https://ap.galaxians.org/users/{user}",
      "published": now,
      "to": [
        "https://www.w3.org/ns/activitystreams#Public"
      ],
      "cc": [
        "https://ap.galaxians.org/users/alice/followers"
      ],
      "object": {
        "id": f"https://ap.galaxians.org/users/{user}/statuses/{id}",
        "type": "Note",
        "summary": None,
        "inReplyTo": None,
        "published": now,
        "url": f"https://ap.galaxians.org/@{user}/{id}",
        "attributedTo": f"https://ap.galaxians.org/users/{user}",
        "to": [
          "https://www.w3.org/ns/activitystreams#Public"
        ],
        "cc": [
          f"https://ap.galaxians.org/users/{user}/followers"
        ],
        "sensitive": False,
        "atomUri": f"https://ap.galaxians.org/users/{user}/statuses/{id}",
        "inReplyToAtomUri": None,
        "conversation": "tag:ap.galaxians.org,2022-11-08:objectId=27216681:objectType=Conversation",
        "content": text,
        "contentMap": {
          "en": text
        },
        "attachment": [],
        "tag": [],
        "replies": {
          "id": f"https://ap.galaxians.org/users/{user}/statuses/{id}/replies",
          "type": "Collection",
          "first": {
            "type": "CollectionPage",
            "next": f"https://ap.galaxians.org/users/{user}/statuses/{id}/replies?only_other_accounts=true&page=true",
            "partOf": f"https://ap.galaxians.org/users/{user}/statuses/{id}/replies",
            "items": []
          }
        }
      }
    }



def generate_toot(user, text=None):
    now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    id = str(uuid.uuid4())
    if text is None:
        text = f"Testing Toot {user} {id} {now}"

    STATE[user]['toots'].append({
        'date': now,
        'id': id,
        'text': text,
        'replies': [],
    })
    save_state(STATE)
    toot_from_state(user, id)



@app.route('/')
def index():
    return 'welcome'
cache = {}

@app.route('/.well-known/host-meta')
def hostmeta():
    return Response("""<?xml version="1.0" encoding="UTF-8"?>
<XRD xmlns="http://docs.oasis-open.org/ns/xri/xrd-1.0">
  <Link rel="lrdd" template="https://ap.galaxians.org/.well-known/webfinger?resource={uri}"/>
</XRD>""")

@app.route('/.well-known/webfinger', methods=['GET'])
def webfinger():
    acct = request.args.get("resource")
    user = acct.split(':', 1)[1].split('@')[0]
    resp = {
        "subject": acct,
        "links": [
            {
                "rel": "self",
                "type": "application/activity+json",
                "href": f"https://ap.galaxians.org/users/{user}",
            }
        ]
    }
    return Response(json.dumps(resp), mimetype='application/ld+json')

@app.route('/users/<user>/avatar.png', methods=['GET'])
def avatar(user):
    return send_file('avatar.png', mimetype='image/png')

@app.route('/users/<user>/followers', methods=['GET'])
def followers(user):
    page = request.args.get("page")
    user_details = get_user(user)

    response =  {
      "@context": "https://www.w3.org/ns/activitystreams",
      "id": f"https://ap.galaxians.org/users/{user}/followers",
      "type": "OrderedCollection",
      "totalItems": len(user_details['followers']),
      "partOf": f"https://ap.galaxians.org/users/{user}/followers",
      "orderedItems":user_details['followers'], 
    }
    return Response(json.dumps(response), mimetype='application/ld+json')

@app.route('/users/<user>/following', methods=['GET'])
def following(user):
    page = request.args.get("page")
    user_details = get_user(user)

    response =  {
      "@context": "https://www.w3.org/ns/activitystreams",
      "id": f"https://ap.galaxians.org/users/{user}/following?page=1",
      "type": "OrderedCollection",
      "totalItems": len(user_details['following']),
      #"next": f"https://ap.galaxians.org/users/{user}/following?page=2",
      "partOf": f"https://ap.galaxians.org/users/{user}/following",
      "orderedItems":user_details['following'], 
    }
    return Response(json.dumps(response), mimetype='application/ld+json')


@app.route('/users/<user>/collections/tags', methods=['GET'])
def collections_tags(user):
    page = request.args.get("page")
    user_details = get_user(user)

    response = {
      "@context": "https://www.w3.org/ns/activitystreams",
      "id": f"https://ap.galaxians.org/users/{user}/collections/tags",
      "type": "Collection",
      "totalItems": 0,
      "tags": [],
    }
    return Response(json.dumps(response), mimetype='application/ld+json')

@app.route('/users/<user>/collections/featured', methods=['GET'])
def collections_featured(user):
    page = request.args.get("page")
    user_details = get_user(user)

    toots = [toot_from_state(user, x['id']) for x in STATE[user]['toots'] if x.get('pinned', False)]
    response = {
      "@context": [
        "https://www.w3.org/ns/activitystreams",
        {
          "ostatus": "http://ostatus.org#",
          "atomUri": "ostatus:atomUri",
          "inReplyToAtomUri": "ostatus:inReplyToAtomUri",
          "conversation": "ostatus:conversation",
          "sensitive": "as:sensitive",
          "toot": "http://joinmastodon.org/ns#",
          "votersCount": "toot:votersCount",
          "Hashtag": "as:Hashtag"
        }
      ],
      "id": f"https://ap.galaxians.org/users/{user}/collections/featured",
      "type": "OrderedCollection",
      "totalItems": len(toots),
      "orderedItems": [toots],
    }
    return Response(json.dumps(response), mimetype='application/ld+json')

@app.route('/users/<user>/outbox', methods=['GET'])
def outbox(user):
    page = request.args.get("page")
    user_details = get_user(user)

    toots = [toot_from_state(user, x['id']) for x in STATE[user]['toots']]
    response =  {
      "@context": [
        "https://www.w3.org/ns/activitystreams",
        {
          "ostatus": "http://ostatus.org#",
          "atomUri": "ostatus:atomUri",
          "inReplyToAtomUri": "ostatus:inReplyToAtomUri",
          "conversation": "ostatus:conversation",
          "sensitive": "as:sensitive",
          "toot": "http://joinmastodon.org/ns#",
          "votersCount": "toot:votersCount",
          "Hashtag": "as:Hashtag"
        }
      ],
      "id": f"https://ap.galaxians.org/users/{user}/following",
      "type": "OrderedCollection",
      "totalItems": len(toots),
      #"next": f"https://ap.galaxians.org/users/{user}/outbox?page=true",
      #"prev": f"https://ap.galaxians.org/users/{user}/outbox?page=true",
      "orderedItems": toots, 
    }
    return Response(json.dumps(response), mimetype='application/ld+json')


@app.route('/users/<user>.json', methods=['GET'])
def userinfo_json(user):
	return _userinfo(user)

@app.route('/users/<user>', methods=['GET'])
def userinfo_html(user):
	return _userinfo(user)

def _userinfo(user):
    user_details = get_user(user)
    resp = {
      "@context": [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
        {
          "Curve25519Key": "toot:Curve25519Key",
          "Device": "toot:Device",
          "Ed25519Key": "toot:Ed25519Key",
          "Ed25519Signature": "toot:Ed25519Signature",
          "EncryptedMessage": "toot:EncryptedMessage",
          "PropertyValue": "schema:PropertyValue",
          "alsoKnownAs": {
            "@id": "as:alsoKnownAs",
            "@type": "@id"
          },
          "cipherText": "toot:cipherText",
          "claim": {
            "@id": "toot:claim",
            "@type": "@id"
          },
          "deviceId": "toot:deviceId",
          "devices": {
            "@id": "toot:devices",
            "@type": "@id"
          },
          "discoverable": "toot:discoverable",
          "featured": {
            "@id": "toot:featured",
            "@type": "@id"
          },
          "featuredTags": {
            "@id": "toot:featuredTags",
            "@type": "@id"
          },
          "fingerprintKey": {
            "@id": "toot:fingerprintKey",
            "@type": "@id"
          },
          "focalPoint": {
            "@container": "@list",
            "@id": "toot:focalPoint"
          },
          "identityKey": {
            "@id": "toot:identityKey",
            "@type": "@id"
          },
          "manuallyApprovesFollowers": "as:manuallyApprovesFollowers",
          "messageFranking": "toot:messageFranking",
          "messageType": "toot:messageType",
          "movedTo": {
            "@id": "as:movedTo",
            "@type": "@id"
          },
          "publicKeyBase64": "toot:publicKeyBase64",
          "schema": "http://schema.org#",
          "suspended": "toot:suspended",
          "toot": "http://joinmastodon.org/ns#",
          "value": "schema:value"
        }
      ],
      "attachment": [
        {
          "type": "PropertyValue",
          "name": "Pronouns",
          "value": "it/she"
        },
      ],
      "devices": f"https://ap.galaxians.org/users/{user}/collections/devices",
      "discoverable": True,
      "endpoints": {
        "sharedInbox": "https://ap.galaxians.org/inbox"
      },
      "featured": f"https://ap.galaxians.org/users/{user}/collections/featured",
      "featuredTags": f"https://ap.galaxians.org/users/{user}/collections/tags",
      "followers": f"https://ap.galaxians.org/users/{user}/followers",
      "following": f"https://ap.galaxians.org/users/{user}/following",
      "icon": {
        "mediaType": "image/png",
        "type": "Image",
        "url": f"https://ap.galaxians.org/users/{user}/avatar.png"
      },
      "id": f"https://ap.galaxians.org/users/{user}",
      "inbox": f"https://ap.galaxians.org/users/{user}/inbox",
      "manuallyApprovesFollowers": False,
      "name": user_details['name'],
      "outbox": f"https://ap.galaxians.org/users/{user}/outbox",
      "preferredUsername": f"{user}",
      "publicKey": {
        "id": f"https://ap.galaxians.org/users/{user}#main-key",
        "owner": "https://ap.galaxians.org/users/{user}",
        "publicKeyPem": PUBKEY,
      },
      "published": "2018-08-12T00:00:00Z", # Joined Date
      "summary": "Owned by @hexylena@tech.lgbt",
      "type": user_details['type'],
      "url": f"https://ap.galaxians.org/@{user}"
    }
    return Response(json.dumps(resp), mimetype='application/ld+json')

@app.route('/inbox', methods=['POST'])
def shared_inbox():
    print("SHARED INBOX")
    print(request.headers)
    print(request.get_json())
    return Response(json.dumps({}), mimetype='application/ld+json', status=202)

@app.route('/users/<user>/inbox', methods=['GET', 'POST'])
def inbox(user):
    print(f"USER INBOX: {user}")
    print(request.headers)
    try:
        body = request.get_json()
        print(body)
        if body['type'] == 'Undo':
            actor = body['actor']
        elif body['type'] == 'Follow':
            print("New Follower!")
            STATE[user]['followers'].append(body['actor'])
            save_state(STATE)

        return Response('{}', mimetype='application/ld+json', status=202)
    except:
        pass

    # Unfollow: 
    # {'@context': 'https://www.w3.org/ns/activitystreams', 'id': 'https://mastodon.social/users/hexylena#follows/10418834/undo', 'type': 'Undo', 'actor': 'https://mastodon.social/users/hexylena', 'object': {'id': 'https://mastodon.social/316e86fa-d8b8-4ab1-a306-29aab8b75b64', 'type': 'Follow', 'actor': 'https://mastodon.social/users/hexylena', 'object': 'https://ap.galaxians.org/users/alice.json'}}
    # Follow: 
    # {'@context': 'https://www.w3.org/ns/activitystreams', 'id': 'https://mastodon.social/6f5bd891-ca6b-4760-8134-0001a63c8233', 'type': 'Follow', 'actor': 'https://mastodon.social/users/hexylena', 'object': 'https://ap.galaxians.org/users/alice.json'}

    # Signature: keyId="https://mastodon.social/users/hexylena#main-key",algorithm="rsa-sha256",headers="(request-target) host date digest content-type",signature="rB5wnVGMpNQGuNKKcADxqLBXGV1lIFwHlpTAIM/QxVBXtjKZkS56RLKk1a8l05f/pwZmXdVnBjjKWKQyEKWpc8OA7uWrHz9hRJx8NpRDwXWFH5U/VwZ8cHxafEjXkgkthIRmYb6znnk2rTuPrXGTh92khCJmoEcn5zcDU9tvmFdPokgm7d4n7rU5ubAaEywnGvWeN2Yeb9/z/6lhgiSFsZUMLHt7zhP6S3e1Vy0y1pWj3GqrPjivBQop4V73d2yspUn+w1RWeYgdbqlD/w4NjgsRL/hkSSVLPoZxlYSapzeozqUKYJ1iq0I+5Le0v9Wx6P6f5zII3JI6qFGH5cssSg=="

    toots = [toot_from_state(user, x['id']) for x in STATE[user]['toots']]
    response =  {
      "@context": [
        "https://www.w3.org/ns/activitystreams",
        {
          "ostatus": "http://ostatus.org#",
          "atomUri": "ostatus:atomUri",
          "inReplyToAtomUri": "ostatus:inReplyToAtomUri",
          "conversation": "ostatus:conversation",
          "sensitive": "as:sensitive",
          "toot": "http://joinmastodon.org/ns#",
          "votersCount": "toot:votersCount",
          "Hashtag": "as:Hashtag"
        }
      ],
      "id": f"https://ap.galaxians.org/users/{user}/inbox",
      "type": "OrderedCollection",
      "totalItems": len(toots),
      #"next": f"https://ap.galaxians.org/users/{user}/outbox?page=true",
      #"prev": f"https://ap.galaxians.org/users/{user}/outbox?page=true",
      "orderedItems": toots, 
    }
    return Response(json.dumps(response), mimetype='application/ld+json')


    
