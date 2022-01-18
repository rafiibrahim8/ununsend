import re
import json
from urllib.parse import unquote

from . import utils

class DiscordAttachment:
    def __init__(self, atype, url, file_name):
        self.__atype = atype
        self.__url = url
        self.__file_name = file_name
    
    @property
    def atype(self):
        return self.__atype
    
    @property
    def url(self):
        return self.__url
    
    @property
    def file_name(self):
        return self.__file_name

class DiscordNS:
    def __init__(self, all_msg_hook, unsent_hook):
        self.__all_hook = all_msg_hook
        self.__unsent_hook = unsent_hook
    
    @staticmethod
    def __get_file_name(url):
        FILE_NAME_REGEX = r'(?<=\/)[^\/\?#]+(?=[^\/]*$)' # Copied from: https://stackoverflow.com/a/56258202/13205702 
        start = url.index('u=h') + 2
        url = unquote(url[start:])
        if re.findall(r'([0-9]{15}_n\.[a-z]*)', url):
            return re.findall(FILE_NAME_REGEX, url)[0], True
        return url, False

    def __get_head(self, name, thread_name, ntype):
        notif_text = f'**{name}** *{ntype}* a message'
        if thread_name:
            notif_text += f' on thread *{thread_name}*'
        notif_text += '.\n'
        return notif_text

    @staticmethod
    def __get_attachment_type(filename):
        pass

    def __resolve_attachments(self, attachments):
        attch = []
        for url in attachments:
            try:
                file_name, is_attachment = self.__get_file_name(url)
                atype = self.__get_attachment_type(file_name)
                if is_attachment:
                    attch.append(DiscordAttachment(atype, url, file_name))
            except:
                utils.DebugDiscord().error(f'Attachmet Resolve Error.\nURL: {url}')

        return attch
        
    def __parse_message(self, message):
        if isinstance(message, str):
            message = json.loads(message)
        
        embeds = list()

        if message.get('sticker'):
            embeds.append({'thumbnail':{'url': message['sticker']}})
        if message['text']:
            embeds.append({'description': message['text']})
        if message.get('attachments'):
            attachment_box = ''
            for i, url in enumerate(message['attachments'], start=1):
                attachment_box+= f':paperclip: [Attachment-{i}]({url})\n'
            embeds.append({'description': attachment_box.strip()})

        return embeds

    
    def notification_sent(self, name, message, thread_name=None):
        jdata = {'content': self.__get_head(name, thread_name, 'sent')}
        
        



