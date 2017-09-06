import datetime
import requests

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import exists

from sqlalchemy_declare import *

engine = create_engine('sqlite:///vk.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()


API_VERSION = 5.67
API_ID = 'PUT API ID HERE'
ACCESS_TOKEN = 'PUT YOUR ACCESS TOKEN HERE'
proxies = {
    'http': '',
    'https': ''
}


def get_all_dialogs():
    params = {
        'v': API_VERSION,
        'access_token': ACCESS_TOKEN
    }
    dialogs = requests.get(
        'https://api.vk.com/method/messages.getDialogs',
        proxies=proxies,
        params=params
    )
    for dialog in dialogs.json()['response']['items']:
        add_user_if_not_exists(dialog['message']['user_id'])
    return [dialog['message']['user_id'] for dialog in dialogs.json()['response']['items']]


def save_photo(photo_id):
    params = {
        'v': API_VERSION,
        'access_token': ACCESS_TOKEN,
        'photos': photo_id,
        'photo_sizes': 1
    }
    photo = requests.get(
        'https://api.vk.com/method/photos.getById',
        proxies=proxies,
        params=params
    )
    r = requests.get(photo.json()['response'][0]["sizes"][-1]['src'], proxies=proxies)
    with open('img/%s.jpg' % photo.json()['response'][0]["id"], 'wb') as f:
        f.write(r.content)


def get_video_link(video_id):
    params = {
        'v': API_VERSION,
        'access_token': ACCESS_TOKEN,
        'videos': video_id
    }
    video = requests.get(
        'https://api.vk.com/method/video.get',
        proxies=proxies,
        params=params
    )
    return video.json()['response']["items"][0]['player']


def save_doc(doc_id):
    params = {
        'v': API_VERSION,
        'access_token': ACCESS_TOKEN,
        'docs': doc_id
    }
    doc = requests.get(
        'https://api.vk.com/method/docs.getById',
        proxies=proxies,
        params=params
    )
    r = requests.get(doc.json()['response'][0]["url"], proxies=proxies)
    with open('docs/%s.%s' % (doc.json()['response'][0]["title"], doc.json()['response'][0]["ext"]), 'wb') as f:
        f.write(r.content)


def get_wall_entry(wall_id):
    params = {
        'v': API_VERSION,
        'access_token': ACCESS_TOKEN,
        'posts': wall_id
    }
    wall = requests.get(
        'https://api.vk.com/method/wall.getById',
        proxies=proxies,
        params=params
    )
    return wall


def get_group_name(group_id):
    params = {
        'v': API_VERSION,
        'access_token': ACCESS_TOKEN,
        'group_id': abs(group_id)
    }
    group = requests.get(
        'https://api.vk.com/method/groups.getById',
        proxies=proxies,
        params=params
    )
    return group.json()["response"][0]["name"]


def get_user_name(user_id):
    params = {
        'v': API_VERSION,
        'access_token': ACCESS_TOKEN,
        'user_ids': user_id
    }
    user = requests.get(
        'https://api.vk.com/method/users.get',
        proxies=proxies,
        params=params
    )
    return user.json()["response"][0]["first_name"], user.json()["response"][0]["last_name"]


def add_user_if_not_exists(user_id):
    first_name, second_name = get_user_name(user_id)
    user_exists = session.query(
        exists().where(
            and_(
                User.first_name == first_name,
                User.second_name == second_name
            )
        )
    ).scalar()
    if not user_exists:
        session.add(User(
            id=user_id,
            first_name=first_name,
            second_name=second_name
        ))


def parse_attachment(a, msg_id, wall_id):
    if a["type"] == "audio":
        att = Attachment(
            type_id=1,
            name=a['audio']['artist'] + a['audio']['title'],
            message_id=msg_id,
            wall_id=wall_id
        )
        session.add(att)
    elif a["type"] == "photo":
        if a["photo"]["id"] != 0:
            save_photo('%s_%s_%s' % (a["photo"]["owner_id"], a["photo"]["id"], a["photo"]["access_key"]))
            att = Attachment(
                type_id=2,
                name=a["photo"]["id"],
                link="img/%s.jpg" % a["photo"]["id"],
                message_id=msg_id, wall_id=wall_id
            )
            session.add(att)
    elif a["type"] == "video":
        link = get_video_link('%s_%s_%s' % (a["video"]["owner_id"], a["video"]["id"], a["video"]["access_key"]))
        att = Attachment(
            type_id=3,
            name=a["video"]["title"],
            link=link,
            message_id=msg_id,
            wall_id=wall_id
        )
        session.add(att)
    elif a["type"] == "doc":
        save_doc('%s_%s_%s' % (a["doc"]["owner_id"], a["doc"]["id"], a["doc"]["access_key"]))
        att = Attachment(
            type_id=4,
            name=a['doc']['title'],
            message_id=msg_id,
            wall_id=wall_id
        )
        session.add(att)
    elif a["type"] == "link":
        att = Attachment(
            type_id=5,
            name=a["link"]["url"],
            link=a["link"]["url"],
            message_id=msg_id,
            wall_id=wall_id
        )
        session.add(att)
    session.commit()


def process_message(message, user_id, msg_id=None, is_forwarded=False):

    if is_forwarded:
        msg = Message(
            from_id=message['user_id'],
            text=message['body'],
            time=datetime.datetime.utcfromtimestamp(message['date'])
        )
        session.add(msg)
        session.flush()
        fwd_message_id = msg.id

        fwd = Message_FWD(
            message_id=msg_id,
            fwd_message_id=fwd_message_id
        )

        session.add(fwd)

        add_user_if_not_exists(message['user_id'])

    else:
        msg = Message(
            from_id=message['from_id'],
            text=message['body'],
            time=datetime.datetime.fromtimestamp(message['date'])
        )
        session.add(msg)
        session.flush()
        msg_id = msg.id

    attachments = message.get('attachments', tuple())
    for a in attachments:
        if is_forwarded:
            parse_attachment(a, fwd_message_id, None)
        else:
            parse_attachment(a, msg_id, None)
        if a["type"] == "wall":
            wall = get_wall_entry('%s_%s' % (a["wall"]["from_id"], a["wall"]["id"])).json()["response"][0]
            group_id = wall["owner_id"]
            group_name = get_group_name(group_id)
            w = Wall(
                owner_name=group_name,
                text=wall["text"],
                message_id=msg_id
            )
            session.add(w)
            session.flush()
            wall_id = w.id

            wall_att = wall["attachments"]
            for wa in wall_att:
                parse_attachment(wa, None, wall_id)

    fwd_messages = message.get('fwd_messages', tuple())
    for fwd_message in fwd_messages:
        if is_forwarded:
            process_message(fwd_message, message['user_id'], fwd_message_id, is_forwarded=True)
        else:
            process_message(fwd_message, message['from_id'], msg_id, is_forwarded=True)
    session.commit()


def get_dialog_history(user_id):
    params = {
        'v': API_VERSION,
        'access_token': ACCESS_TOKEN,
        'user_id': user_id,
        'count': 200,
        'offset': 0,
        'rev': 1
    }

    msg_history = requests.get(
        'https://api.vk.com/method/messages.getHistory',
        proxies=proxies,
        params=params
    )
    while msg_history.json()['response']['items']:
        for message in msg_history.json()['response']['items']:
            process_message(message, user_id)
        params['offset'] += 200
        msg_history = requests.get(
            'https://api.vk.com/method/messages.getHistory',
            proxies=proxies,
            params=params
        )


def main():
    get_dialog_history(get_all_dialogs())


if __name__ == "__main__":
    main()
