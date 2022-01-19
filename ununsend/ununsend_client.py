import fbchat.models as models
from fbchat import Client
from fbchat import Message, ThreadType
import datetime
import time

from . import utils
from .notification_sender import WebsiteUpdater, DiscordNotificationSender

class Listener(Client):
    def __init__(self, cookies, dbms, clients, socket):
        ua = dbms.get_website_stuff('user_agent')
        super().__init__(None, None, session_cookies=cookies, user_agent=ua, auto_reconnect_after=30)
        self.__dbms = dbms
        self.__website_updater = WebsiteUpdater(socket, clients)
        self.__discord_ns = DiscordNotificationSender(dbms.get_website_stuff('discord_all_message'), dbms.get_website_stuff('discord'))

    @staticmethod
    def __resolve_attachments(attachments):
        if attachments == []:
            return
        resolved = []
        for attachment in attachments:
            if isinstance(attachment, models.ImageAttachment):
                if attachment.is_animated:
                    resolved.append({'type': 'image', 'url': attachment.animated_preview_url})
                else:
                    resolved.append({'type': 'image', 'url': attachment.large_preview_url})
            
            elif isinstance(attachment, models.AudioAttachment):
                resolved.append({'type': 'audio', 'url': attachment.url, 'filename': attachment.filename})

            elif isinstance(attachment, models.FileAttachment):
                resolved.append({'type': 'file', 'url': attachment.url, 'filename': attachment.name})
            
            elif isinstance(attachment, models.ShareAttachment):
                resolved.append({'type': 'share', 'url': attachment.url})

            elif isinstance(attachment, models.VideoAttachment):
                resolved.append({'type': 'video', 'url': attachment.preview_url, 'filename': attachment.filename})
            
            elif isinstance(attachment, (models.LocationAttachment, models.LiveLocationAttachment)):
                resolved.append({'type': 'location', 'url': f'https://www.google.com/maps?q={attachment.latitude},{attachment.latitude}', 'lat': attachment.latitude, 'long': attachment.longitude})
            else:
                utils.DebugDiscord().error(f'Unknown attachment type: {type(attachment)}')
        return resolved

    def __resolveUserName(self, uid):
        user = self.__dbms.unsentManager.queryContact(uid)
        
        if user == None:
            try:
                userName = self.fetchUserInfo(uid)[uid].name
                self.__dbms.unsentManager.addContact(uid, userName)
            except:
                userName = uid
        else:
            userName = user.name
        return userName
    
    def __resolveMessageThreadName(self, thread_id):
        messageThread = self.__dbms.unsentManager.queryMessageThread(thread_id)
        if messageThread != None:
            return messageThread.name
        user = self.__dbms.unsentManager.queryContact(thread_id) # if it is a user thread
        if user != None:
            self.__dbms.unsentManager.addMessageThread(thread_id, user.name)
            return user.name
        
        try:
            thread_name = self.fetchThreadInfo(thread_id)[thread_id].name
            if thread_name != None:
                self.__dbms.unsentManager.addMessageThread(thread_id, thread_name)
                return thread_name
        except:
            pass
        return thread_id

    def onMessage(self, mid=None, author_id=None, message_object=None, ts=None, thread_id=None, **kwargs):
        if author_id == self.uid:
            return
        message = {
            'text': message_object.text,
            'sticker': None if not message_object.sticker else message_object.sticker.url,
            'attachments' : self.__resolve_attachments(message_object.attachments)
        }
        userName = self.__resolveUserName(author_id)
        
        thread_name = None if author_id==thread_id else self.__resolveMessageThreadName(thread_id)
        self.__discord_ns.notification_on_sent(userName, message, thread_name)
        self.__dbms.unsentManager.addMessage(message_id=mid, timestamp=ts, sender=author_id, message=message)
    
    def onMessageUnsent(self, mid=None, author_id=None, ts=None, thread_id=None, **kwargs):
        res = self.__dbms.unsentManager.queryMessage(mid)
        if res == None:
            return
        
        userName = self.__resolveUserName(author_id)
        threadName = self.__resolveMessageThreadName(thread_id)
        self.__dbms.unsentManager.addUnsentMessage(message_id=mid, timestamp=res.timestamp, timestamp_us=ts, sender=author_id, sender_name=userName, message=res.message, thread_id=thread_id, thread_name=threadName)

        thread_name = None if author_id==thread_id else threadName
        self.__discord_ns.notification_on_unsent(userName, res.message,  res.timestamp, ts, thread_name=thread_name)
        self.__website_updater.update_on_website_single(userName, res.message,  res.timestamp, ts, thread_name=thread_name)

def keep_alive(listener, dbms):
    ping_sleep_time = 4 # hours
    ping_active_time = 200 #sec
    while True:
        time.sleep(ping_sleep_time * 3600 - ping_active_time)
        listener.setActiveStatus(True)
        time.sleep(ping_active_time)
        keep_alive_thread = dbms.get_website_stuff('keep_alive_thread')
        if keep_alive_thread:
            ka_text = 'Ununsend keep-alive at ' + datetime.datetime.now(utils.UserTZ.get_tz()).strftime('%Y-%m-%d %H:%M:%S')
            try:
                listener.send(Message(ka_text), keep_alive_thread, ThreadType.GROUP)
            except:
                utils.DebugDiscord().error('Sending keep-alive message failed.')
        listener.setActiveStatus(False)
        uid = dbms.get_last_message_contact_id()
        if uid:
            try:
                listener.getUserActiveStatus(uid)
            except:
                pass

def main(listener, always_active=False):
    listener.listen(always_active)
