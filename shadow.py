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
    m.update(text.encode('utf-8'))
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

        #print u"[{}] {}: {}".format(msg['created_at'], msg['name'], unicode(msg['text']))

    # Send any relay messages (if any)
    if 'relay_message' in config:
        relay_content = config.pop('relay_message')
        send_group_message(config, group, relay_content)

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

    text = unicode(text)

    payload = {
        "message": {
            "source_guid": msg_guid(group['id'], text),
            "text": text
        }
    }

    r = requests.post(build_url(config, 'groups/{}/messages').format(group['id']), data=json.dumps(payload), headers=POST_HEADERS)
    if r.status_code == 201:
        print u"Sent group message {}: {}".format(group['name'], text)
    else:
        print u"Error sending direct message: {} {}".format(r.status_code, r.text)

# Parse and take action on any command sent through DM
def process_direct_command(config, recipient_id, text):

    # Syntax: !relay:<msg>
    # If a direct message with !relay is sent, the following string will be sent as a group message by this bot
    if text.startswith('!relay:'):
        content = text.split(':')[1]
        config['relay_message'] = content

    # Syntax: !timed <mins from now> <msg>
    # Add a timed message
    elif text.startswith('!timed:'):
        segs = text.split(':')
        mins = int(segs[1])
        content = segs[2]

        config['timed_messages'].append({
            'time': int(time.time()) + (mins * 60),
            'text': content
        })

    # Syntax: !group:<group name>
    # Switch the target group by name on the next cycle
    elif text.startswith('!group:'):
        target_group_name = text.split(':')[1]
        config['target_group_name'] = target_group_name

    # Syntax: !cleartimed
    # Clear out timed messages
    elif text.startswith('!cleartimed'):
        config['timed_messages'] = []

    # Syntax: !config
    # Dump the config.json without the api token
    elif text.startswith('!config'):
        sent_config = {}
        sent_config.update(config)
        sent_config.pop('api_token')

        send_direct_message(config, recipient_id, json.dumps(sent_config, indent=4))

    else:
        pass

# Check for any new direct messages since the last run, reply with a Meow
def check_direct_messages(config):
    r = requests.get(build_url(config, 'chats'))

    resp = r.json()['response']

    # Get new direct conversations
    print "Checking new direct messages.."
    for msg in resp:

        # If the message was before the last runtime, OR sent by me, we've already seen it
        if msg['updated_at'] < config['last_runtime'] or msg['last_message']['sender_id'] == config['my_user_id']:
            continue

        text = msg['last_message']['text']
        #print u"[{}] {}: {}".format(msg['created_at'], msg['other_user']['name'], unicode(text))

        other_user_id = msg['other_user']['id']

        # Check for a direct messaged command
        if text.startswith('!'):
            process_direct_command(config, other_user_id, text)

        else:
            # Otherwise, just reply to any new messages with a Meow
            send_direct_message(config, other_user_id, "Meow")

# Send a direct message to another user by id
def send_direct_message(config, recipient_id, text):

    text = unicode(text)

    payload = {
        "direct_message": {
            "source_guid": msg_guid(recipient_id, text),
            "recipient_id": recipient_id,
            "text": text
        }
    }

    r = requests.post(build_url(config, 'direct_messages'), data=json.dumps(payload), headers=POST_HEADERS)
    if r.status_code == 201:
        print u"Sent direct message to {}: {}".format(recipient_id, text)
    else:
        print u"Error sending direct message: {} {}".format(r.status_code, r.text)

def main():

    # Read config
    with open(os.path.join(os.path.dirname(__file__), 'config.json')) as fh:
        config = json.load(fh)

    # Set last runtime as 0 if never been run before
    if 'last_runtime' not in config:
        config['last_runtime'] = 0

    # Get my own user info
    get_my_info(config)

    # Check direct messages
    check_direct_messages(config)

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

    # Set the new last runtime
    config['last_runtime'] = int(time.time())

    # Write back configuration
    with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'w+') as fh:
        fh.write(json.dumps(config, indent=4))

if __name__ == '__main__':
    main()
