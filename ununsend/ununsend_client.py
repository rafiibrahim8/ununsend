import json
import requests
import os
import fbchat.models as models
from fbchat import Client, FBchatException
import datetime
import threading
import time

from . import utils

class BDT(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=6)
    def dst(self, dt):
        return datetime.timedelta(hours=6)
    def tzname(self, dt):
        return 'Bangladesh Standard Time'

def make_notification_text(name, message, sent_at, unsent_at):
    notif_text = f'{name} unsent a message.\n'
    message = json.loads(message)
    if message['text']:
        notif_text += 'Text: {}\n'.format(message['text'])
    if message['sticker']:
        notif_text += 'Sticker: {}\n'.format(message['sticker'])
    if message['attachments']:
        for i, attachment in enumerate(message['attachments'], start=1):
            notif_text += 'Attachment({}): {}\n'.format(i, attachment)

    sent_at = datetime.datetime.fromtimestamp(sent_at/1000, BDT()).strftime('%Y-%m-%d %H:%M:%S')
    unsent_at = datetime.datetime.fromtimestamp(unsent_at/1000, BDT()).strftime('%Y-%m-%d %H:%M:%S')

    notif_text += f'Sent Time: {sent_at}\nUnsent Time: {unsent_at}'

    return notif_text

def make_notification_text_from_obj(unsentMessage):
    return make_notification_text(unsentMessage.sender_name, unsentMessage.message, unsentMessage.timestamp, unsentMessage.timestamp_us)


class Listener(Client):
    def __init__(self, cookies, dbms, clients, socket):
        super().__init__(None, None, session_cookies=cookies)
        self.__dbms = dbms
        self.__clients = clients
        self.__socket = socket

    @staticmethod
    def __resolveAttachmentx(attachments):
        if attachments == []:
            return
        resolved = []
        for attachment in attachments:
            if isinstance(attachment, models.ImageAttachment):
                if attachment.is_animated:
                    resolved.append(attachment.animated_preview_url)
                else:
                    resolved.append(attachment.large_preview_url)
            
            elif isinstance(attachment, (models.AudioAttachment, models.FileAttachment, models.ShareAttachment)):
                resolved.append(attachment.url)

            elif isinstance(attachment, models.VideoAttachment):
                resolved.append(attachment.preview_url)
            
            elif isinstance(attachment, (models.LocationAttachment, models.LiveLocationAttachment)):
                resolved.append(f'Latitude: {attachment.latitude}, Longitude: {attachment.longitude}')
            
            else:
                print('Unknown attachment type.')
        return resolved

    def __updateOnWebsite(self, notif_text):
        for i in self.__clients:
            utils.update_on_website(self.__socket, notif_text, i)

    def __send_notification_discord(self, notif_text):
        discord_hook = self.__dbms.get_website_stuff('discord')
        if not discord_hook:
            return
        try:
            requests.post(discord_hook, json={'content': notif_text})
        except:
            pass

    def __send_notification_pb(self, notif_text):
        access_token = self.__dbms.get_website_stuff('push_bullet')
        if not access_token:
            return
        notif_text = [i.strip() for i in notif_text.split('\n') if i.strip()]
        jdata = {
        'type': 'note',
        'title': notif_text[0],
        'body': '\n'.join(notif_text[1:])
        }
        try:
            requests.post('https://api.pushbullet.com/v2/pushes', headers={'Access-Token': access_token}, json=jdata)
        except:
            pass
    def __send_notifications(self, notif_text):
        self.__send_notification_discord(notif_text)
        self.__send_notification_pb(notif_text)

    def onMessage(self, mid=None, author_id=None, message_object=None, ts=None, **kwargs):
        if author_id == self.uid:
            return
        message = {
            'text': message_object.text,
            'sticker': None if not message_object.sticker else message_object.sticker.url,
            'attachments' : Listener.__resolveAttachmentx(message_object.attachments)
        }
        self.__dbms.unsentManager.addMessage(message_id=mid, timestamp=ts, sender=author_id, message=message)
    
    
    def onMessageUnsent(self, mid=None, author_id=None, ts=None, **kwargs):
        print('New Message Unsent')
        res = self.__dbms.unsentManager.queryMessage(mid)
        if res == None:
            return
        
        user = self.__dbms.unsentManager.queryContact(author_id)
        
        if user == None:
            try:
                userName = self.fetchUserInfo(author_id)[author_id].name
                self.__dbms.unsentManager.addContact(author_id, userName)
            except FBchatException:
                userName = author_id
        else:
            userName = user.name
        
        self.__dbms.unsentManager.addUnsentMessage(message_id=mid, timestamp=res.timestamp, timestamp_us=ts, sender=author_id, sender_name=userName, message=res.message)
        
        # send_notification(userName, res.message, res.timestamp, ts)
        notif_text = make_notification_text(userName, res.message, res.timestamp, ts)
        self.__send_notifications(notif_text)
        self.__updateOnWebsite(notif_text)


def main(listener, always_active=False):
    listener.listen(always_active)


