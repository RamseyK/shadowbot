# A GroupMe bot
# https://github.com/RamseyK/shadowbot

import requests
import time
import json
import hashlib
import os

BASE_URL = "https://api.groupme.com/v3"

POST_HEADERS = {'Content-Type': 'application/json', 'Accept': 'text/plain'}

def build_url(config, endpoint):
    return "{}/{}?token={}".format(BASE_URL, endpoint, config['api_token'])

def msg_guid(recipient_id, text):
    m = hashlib.md5()
    m.update(recipient_id)
    m.update(text)
    m.update(str(time.time()))
    return str(m.hexdigest())

# Get current user account id and set it in the config
def get_my_info(config):
    r = requests.get(build_url(config, 'users/me'))
    resp = r.json()['response']

    config['my_user_id'] = resp['id']

# Returns the group object of the target group given the name of the group
# Returns None
def get_target_group(config):
    target_group = None
    target_name = config['target_group_name']

    r = requests.get(build_url(config, 'groups'))
    resp = r.json()['response']

    #print "Groups:"
    for group in resp:
        #print "[{}, {}]".format(group['id'], group['name'])

        if target_name.lower() in group['name'].lower():
            target_group = group

    return target_group

# Check for any new group messages since the last run
def check_group_messages(config, group):
    r = requests.get(build_url(config, 'groups/{}/messages'.format(group['id'])))
    resp = r.json()['response']

    # Get new messages
    print "Checking group messages.."
    for msg in resp['messages']:

        # If the message was before the last runtime, OR sent by me, we've already seen it
        if msg['created_at'] < config['last_runtime'] or msg['sender_id'] == config['my_user_id']:
            continue

        print "[{}] {}: {}".format(msg['created_at'], msg['name'], msg['text'])

# Send a timed message from the config to a group
def send_timed_messages(config, group):

    cur_time = int(time.time())
    saved_messages = []

    print "Checking for any timed messages to send.."

    # Check if theres any new messages in the config that we're past due to send
    for msg in config['timed_messages']:

        # Message is still in the future, save and continue
        if cur_time < msg['time']:
            saved_messages.append(msg)
            continue

        send_group_message(config, group, msg['text'])

    # Write back only saved messages
    config['timed_messages'] = saved_messages

# Send a group message
def send_group_message(config, group, text):

    payload = {
        "message": {
            "source_guid": msg_guid(group['id'], text),
            "text": text
        }
    }

    r = requests.post(build_url(config, 'groups/{}/messages').format(group['id']), data=json.dumps(payload), headers=POST_HEADERS)
    if r.status_code == 201:
        print "Sent group message {}: {}".format(group['name'], text)
    else:
        print "Error sending direct message: {} {}".format(r.status_code, r.text)

# Check for any new direct messages since the last run, reply with a Meow
def check_direct_messages(config):
    r = requests.get(build_url(config, 'chats'))

    resp = r.json()['response']

    # Get new direct messages
    print "Checking new direct messages.."
    for msg in resp:

        # If the message was before the last runtime, OR sent by me, we've already seen it
        if msg['updated_at'] < config['last_runtime'] or msg['last_message']['sender_id'] == config['my_user_id']:
            continue

        print "[{}] {}: {}".format(msg['created_at'], msg['other_user']['name'], msg['last_message']['text'])

        conversation_id = msg['last_message']['conversation_id']
        other_user_id = msg['other_user']['id']

        # Reply to any new messages with a Meow
        send_direct_message(config, other_user_id, "Meow")

# Send a direct message to another user by id
def send_direct_message(config, recipient_id, text):

    payload = {
        "direct_message": {
            "source_guid": msg_guid(recipient_id, text),
            "recipient_id": recipient_id,
            "text": text
        }
    }

    r = requests.post(build_url(config, 'direct_messages'), data=json.dumps(payload), headers=POST_HEADERS)
    if r.status_code == 201:
        print "Sent direct message to {}: {}".format(recipient_id, text)
    else:
        print "Error sending direct message: {} {}".format(r.status_code, r.text)

def main():

    # Read config
    with open(os.path.join(os.path.dirname(__file__), 'config.json')) as fh:
        config = json.load(fh)

    # Set last runtime as 0 if never been run before
    if 'last_runtime' not in config:
        config['last_runtime'] = 0

    # Get my info
    get_my_info(config)

    # Get target group
    group = get_target_group(config)
    if not group:
        print "Could not find target group"
        exit(-1)

    print "Group: {}".format(group)

    # Check group messages for mentions
    check_group_messages(config, group)

    # Send timed group messages
    send_timed_messages(config, group)

    # Check direct messages
    check_direct_messages(config)

    # Set the new last runtime
    config['last_runtime'] = int(time.time())

    # Write back configuration
    with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'w+') as fh:
        fh.write(json.dumps(config, indent=4))

if __name__ == '__main__':
    main()