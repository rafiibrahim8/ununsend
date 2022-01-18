from datetime import datetime
import re
import json
import requests
from urllib.parse import unquote

from . import utils

class DiscordNotificationSender:
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

    def __resove_share_embed(self, url):
        og = utils.opengraph_lookup(url)
        embed = dict()
        if og.get('image'):
            embed['thumbnail'] = {'url': og['image']}
        if og.get('description'):
            embed['description'] = og['description']
        if og.get('title'):
            embed['title'] = og['title']
            embed['url'] = url
        else:
            embed['title'] = url
        
        return embed

    def __resove_location_embed(attachment):
        og = utils.opengraph_lookup(attachment['url'])
        embed = dict()
        if og.get('image'):
            embed['thumbnail'] = {'url': og['image']}
        embed['description'] = f'**Location Data**\n Latitude: {attachment["lat"]}, Longitude: {attachment["long"]}'
        if og.get('title'):
            embed['title'] = og['title']
            embed['url'] = attachment['url']
        
        return embed
    
    def __resolve_attachments(self, attachments):
        individual_embed = []
        aio_embed = ''
        for attachment in attachments:
            if attachment['type'] == 'image':
                individual_embed.append({'image': {'url':attachment['url']}})
            elif attachment['type'] == 'audio':
                aio_embed += f':musical_note: [{self.__get_file_name(attachment["url"])}]({attachment["url"]})\n'
            elif attachment['type'] == 'file':
                aio_embed += f':paperclip: [{self.__get_file_name(attachment["url"])}]({attachment["url"]})\n'
            elif attachment['type'] == 'video':
                aio_embed += f':movie_camera: [{self.__get_file_name(attachment["url"])}]({attachment["url"]})\n'
            elif attachment['type'] == 'share':
                individual_embed.append(self.__resove_share_embed(attachment['url']))
            elif attachment['type'] == 'location':
                individual_embed.append(self.__resove_location_embed(attachment))
            
        if aio_embed:
            individual_embed.append({'description': aio_embed.strip()})

        return individual_embed
        
    def __parse_message(self, message, footer_text=None):
        if isinstance(message, str):
            message = json.loads(message)
        
        embeds = []

        if message.get('sticker'):
            embeds.append({'thumbnail':{'url': message['sticker']}})
        if message.get('text'):
            embeds.append({'description': message['text']})
        if message.get('attachments'):
            for i in self.__resolve_attachments(message['attachments']):
                embeds.append(i)
        if footer_text:
            embeds.append({'footer': {'text': footer_text}})
        return embeds

    def __get_unsend_footer(self, sent_at, unsent_at):
        sent_at = datetime.fromtimestamp(sent_at, utils.UserTZ.get_tz()).strftime('%Y-%m-%d %H:%M:%S')
        unsent_at = datetime.fromtimestamp(unsent_at, utils.UserTZ.get_tz()).strftime('%Y-%m-%d %H:%M:%S')
        return f'Sent at: {sent_at}\nUnsent at: {unsent_at}'

    def __post_to_discord_impl(self, url, jdata):
        try:
            requests.post(url, json=jdata)
        except:
            utils.DebugDiscord().error(f'Discord Notification Failed. Message: {json.dumps(jdata, indent=4)}')

    def __post_to_discord(self, url, json_data):
        jdata = dict()
        jdata['content'] = json_data['content']
        jdata['embeds'] = list()

        for i, e in enumerate(json_data['embeds'], start=1):
            jdata['embeds'].append(e)
            if i == 10:
                self.__post_to_discord_impl(url, jdata)
                jdata.pop('content', None)
                jdata['embeds'] = list()
        
        if jdata['embeds']:
            self.__post_to_discord_impl(url, jdata)
            
    def notification_on_sent(self, name, message, thread_name=None):
        jdata = {'content': self.__get_head(name, thread_name, 'sent'), 'embeds': self.__parse_message(message)}
        self.__post_to_discord(self.__all_hook, jdata)

    def notification_on_unsent(self, name, message, sent_at, unsent_at, thread_name=None):
        jdata = {'content': self.__get_head(name, thread_name, 'unsent'), 'embeds': self.__parse_message(message, self.__get_unsend_footer(sent_at, unsent_at))}
        self.__post_to_discord(self.__unsent_hook, jdata)
        



