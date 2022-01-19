from datetime import datetime
import json
import random
import requests

from . import utils

class DiscordNotificationSender:
    def __init__(self, all_msg_hook, unsent_hook):
        self.__all_hook = all_msg_hook
        self.__unsent_hook = unsent_hook

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
            embed['image'] = {'url': og['image']}
        if og.get('description'):
            embed['description'] = og['description']
        if og.get('title'):
            embed['title'] = og['title']
        else:
            embed['title'] = 'Share Attachment'
        embed['url'] = url
        
        if len(embed['title'])>256:
            embed['title'] = embed['title'][:250] + '...'

        return embed

    def __resove_location_embed(self, attachment):
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
                aio_embed += f':musical_note: [{attachment["filename"]}]({attachment["url"]})\n'
            elif attachment['type'] == 'file':
                aio_embed += f':paperclip: [{attachment["filename"]}]({attachment["url"]})\n'
            elif attachment['type'] == 'video':
                aio_embed += f':movie_camera: [{attachment["filename"]}]({attachment["url"]})\n'
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
    
    @staticmethod
    def get_unsend_footer(sent_at, unsent_at):
        sent_at = datetime.fromtimestamp(sent_at/1000, utils.UserTZ.get_tz()).strftime('%Y-%m-%d %H:%M:%S')
        unsent_at = datetime.fromtimestamp(unsent_at/1000, utils.UserTZ.get_tz()).strftime('%Y-%m-%d %H:%M:%S')
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
            if not e.get('color'):
                e['color'] = random.randint(0, 0xffffff)
            jdata['embeds'].append(e)
            
            if i == 10:
                self.__post_to_discord_impl(url, jdata)
                jdata.pop('content', None)
                jdata['embeds'] = list()
        
        if jdata['embeds']:
            self.__post_to_discord_impl(url, jdata)
            
    def notification_on_sent(self, name, message, thread_name=None):
        if not self.__all_hook:
            return
        jdata = {'content': self.__get_head(name, thread_name, 'sent'), 'embeds': self.__parse_message(message)}
        self.__post_to_discord(self.__all_hook, jdata)

    def notification_on_unsent(self, name, message, sent_at, unsent_at, thread_name=None):
        if not self.__unsent_hook:
            return
        jdata = {'content': self.__get_head(name, thread_name, 'unsent'), 'embeds': self.__parse_message(message, self.get_unsend_footer(sent_at, unsent_at))}
        self.__post_to_discord(self.__unsent_hook, jdata)
        
class WebsiteUpdater:
    def __init__(self, socket, clients):
        self.__socket = socket
        self.__clients = clients
    
    @staticmethod
    def mk_notification(name, message, sent_at, unsent_at, thread_name=None):
        title = f'{name} unsent a message'
        if thread_name:
            title += f' on thread {thread_name}'
        title += '.\n'
    
        if isinstance(message, str):
            message = json.loads(message)
        body = ''

        if message['attachments']:
            for i, attachment in enumerate(message['attachments'], start=1):
                body += 'Attachment[{}]: {}\n'.format(i, attachment['url'] if isinstance(attachment, dict) else attachment) # legacy
        if message['sticker']:
            body += 'Sticker: {}\n'.format(message['sticker'])
        if message['text']:
            body += 'Text: {}\n'.format(message['text'])
        body += f'\n{DiscordNotificationSender.get_unsend_footer(sent_at, unsent_at)}'

        return {'title': title, 'body': body.split('\n')}

    @staticmethod
    def make_website_notif_from_unsend_obj(unsentMessage):
        notif_thread_name = None if unsentMessage.sender==unsentMessage.thread_id else unsentMessage.thread_name
        return WebsiteUpdater.mk_notification(unsentMessage.sender_name, unsentMessage.message, unsentMessage.timestamp, unsentMessage.timestamp_us, thread_name=notif_thread_name)

    @staticmethod
    def update_on_website_bulk(socket, notif_texts, client=None):
        if not isinstance(notif_texts, list):
            notif_texts = [notif_texts]
        if client == None:
            socket.emit('load_messages', json.dumps(notif_texts))
        else:
            socket.emit('load_messages', json.dumps(notif_texts), room=client)

    def update_on_website_single(self, name, message, sent_at, unsent_at, thread_name=None):
        notification = self.mk_notification(name, message, sent_at, unsent_at, thread_name)
        for client in self.__clients:
            self.update_on_website_bulk(self.__socket, notification, client)
