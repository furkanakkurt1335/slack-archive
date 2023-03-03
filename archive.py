import requests, json, os, random, argparse

parser = argparse.ArgumentParser(description='Slack API')
parser.add_argument('--token', type=str, help='Slack API token', required=True)
args = parser.parse_args()
token = args.token # in the form of xoxp-1234567890-1234567890-1234567890-abcd1234
headers = {'Authorization': f'Bearer {token}'}

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

def get_content(url):
    req_get = requests.get(url, headers=headers)
    return json.loads(req_get.content.decode('utf-8'))

slack_archive_path = os.path.join(THIS_DIR, 'Workspace-Archives')
if not os.path.exists(slack_archive_path):
    os.mkdir(slack_archive_path)

team_info_url = 'https://slack.com/api/team.info'
team_name = get_content(team_info_url)['team']['name']
team_folder_path = os.path.join(slack_archive_path, team_name)
if not os.path.exists(team_folder_path):
    os.mkdir(team_folder_path)

conv_types = ['public_channel', 'private_channel', 'im', 'mpim']
for type_t in conv_types:
    type_folder_path = os.path.join(team_folder_path, type_t)
    if not os.path.exists(type_folder_path):
        os.mkdir(type_folder_path)

def get_conversations():
    global conv_types
    conv_list_url = 'https://slack.com/api/conversations.list?limit=1000&types='
    conv_d = {}
    for type_t in conv_types:
        conv_d[type_t] = get_content(conv_list_url + type_t)
    return conv_d

conv_d = get_conversations()

def get_users():
    users_d = {}
    users_list_url = 'https://slack.com/api/users.list?limit=1000'
    users_list = get_content(users_list_url)
    if 'members' not in users_list.keys(): return users_d
    for member in users_list['members']:
        if 'real_name' in member.keys(): users_d[member['id']] = member['real_name']
        else: users_d[member['id']] = member['name']
    return users_d

users_d = get_users()

def get_im_channel_for_user(user_id):
    for conversation in conv_d['channels']:
        if conversation['user'] == user_id:
            return conversation['id']

conversations_history_url = f'https://slack.com/api/conversations.history?limit=1000&channel=' # channel
conversations_replies_url = f'https://slack.com/api/conversations.replies?channel=' # threads
for type_t in conv_types:
    type_folder_path = os.path.join(team_folder_path, type_t)
    conv_l = conv_d[type_t]
    for ch in conv_l['channels']:
        history_t = get_content(conversations_history_url + ch['id'])
        if 'name' in ch.keys(): channel_name = ch['name']
        elif type_t == 'im': channel_name = users_d[ch['user']]
        else: channel_name = ch['id']
        message_file_path = os.path.join(type_folder_path, f'{channel_name}.json')
        message_l = []
        if 'messages' in history_t.keys() and history_t['messages']:
            message_l = history_t['messages']
            while 'has_more' in history_t.keys() and history_t['has_more']:
                next_cursor = history_t['response_metadata']['next_cursor']
                history_t = get_content(conversations_history_url + f'&cursor={next_cursor}')
                if 'messages' in history_t.keys():
                    for message_t in history_t['messages']:
                        if 'thread_ts' in message_t.keys():
                            thread_file_path = message_file_path[:-5] + '-threads.json'
                            with open(thread_file_path, 'a', encoding='utf-8') as thread_f:
                                ts_t = message_t['ts']
                                reply_t = get_content(conversations_replies_url + f'{channel_name}&ts={ts_t}')
                                json.dump(reply_t['messages'], thread_f, indent=4, ensure_ascii=False)
                    message_l += history_t['messages']
            with open(message_file_path, 'w', encoding='utf-8') as f:
                json.dump(message_l, f, indent=4, ensure_ascii=False)

files_list_url = 'https://slack.com/api/files.list'
files = get_content(files_list_url)
if 'files' in files.keys():
    files_folder_path = os.path.join(team_folder_path, 'files')
    os.mkdir(files_folder_path)
    file_l = files['files']
    for file in file_l:
        file_url, file_name, file_type = file['url_private'], file['name'], file['filetype']
        file_get = requests.get(file_url, headers=headers)
        random_path = str(random.randint(100000, 999999))
        file_path = os.path.join(files_folder_path, file_name.replace(f'.{file_type}', f'-{random_path}.{file_type}'))
        with open(file_path, 'wb') as file_f:
            file_f.write(file_get.content)