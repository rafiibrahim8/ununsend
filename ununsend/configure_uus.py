import fbchat
import click
import pytz
import requests
import json
import urllib
import getpass
import re

from .utils import AESCipher, decrypt_cookies
from .ua_getter import UAGetter
from . import colors

def get_int(prompt, default):
    while True:
        try:
            return int(click.prompt(prompt, default=f'{default}'))
        except:
            print('Invalid Input. Try again.')

def get_mbasic_link(link:str):
    try:
        slash = link.index('/', 8)
    except ValueError:
        try:
            slash = link.index('/', 4) # fb.me/hello, m.me/hello
        except:
            return
    return 'https://mbasic.facebook.com' + link[slash:]

class ConfigureUUS:
    def __init__(self, dbms):
        self.__dbms=dbms
    
    def id_u(self, res_dot_text):
        try:
            return re.findall('<a href=\\"\\/.{1,}\\/about\\?lst=[^%]+%3A([^%\\"]+)', res_dot_text)[0]
        except:
            return None

    def check_cookie_whois(self, cookie):
        res = requests.get('https://mbasic.facebook.com/me', cookies=cookie)
        if self.id_u(res.text) != cookie.get('c_user'):
            return None
        return re.findall('<title>(.{1,})<\\/title>+', res.text)[0]

    def check_for_fb_profile(self):
        import browser_cookie3 as bc3
        browsers = {'Chrome': bc3.chrome, 'Firefox': bc3.firefox, 'Chromium': bc3.chromium, 'Edge': bc3.edge}
        cookies = []
        for name, browser in browsers.items():
            try:
                cookie = requests.utils.dict_from_cookiejar(browser(domain_name='facebook.com'))
                user_name = self.check_cookie_whois(cookie)
                if user_name != None:
                    cookies.append({'browser_name': name, 'user_name': user_name, 'cookie': cookie})
            except:
                pass
        return cookies
    
    def get_user_cookie(self):
        print('Checking for messenger profiles on the PC.\nThis may take some time.\nPlease wait...') 
        profiles = []
        for i in self.check_for_fb_profile():
            if i.get('user_name') != 'Facebook – log in or sign up':
                profiles.append(i)
        
        if not profiles:
            print('Unable to find any profile on this PC.\nEnter manually.')
            return self.manual_cookie_in()
            
        while True:
            for i, profile in enumerate(profiles, start=1):
                print(f'{i}. {profile.get("user_name")} on {profile.get("browser_name")}')
            user_input = input('Choose a profile or enter nothing for manual cookie input: ').strip()
            if not user_input:
                return self.manual_cookie_in()
            try: 
                cookie = profiles[int(user_input)-1]
            except: 
                print('Invalid input. Try Again.')
                continue
            print(f'Selected profile: {cookie.get("user_name")}')
            return cookie

    def encrypt_cookies(self, cookies, password):
        aes = AESCipher(password)
        return aes.encrypt(json.dumps(cookies))

    def manual_cookie_in_helper(self, name):
        while True:
            input_ = input(f'Enter cookie {name}: ').strip()
            if input_:
                return input_
            print('Empty input. Enter again.')

    def manual_cookie_in(self):
        cookie = {'wd': '1366x668'}
        required = ['c_user', 'datr', 'sb', 'xs']
        for i in required:
            cookie[i] = self.manual_cookie_in_helper(i)
        user_name =  self.check_cookie_whois(cookie)
        if user_name == None:
            print('Failed to find a valid user with this cookies.')
            return
        print(f'Found user {user_name}')
        return {'user_name': user_name, 'cookie': cookie}

    def get_password_ii(self):
        while True:
            passwd1 = getpass.getpass('Enter password: ').strip()
            passwd2 = getpass.getpass('Enter password again: ').strip()
            if passwd1 == passwd2:
                return passwd1
            print('Passwords doesn\'t match. Try again.')

    def configure_cookie(self):
        cookie = self.__dbms.get_website_stuff('cookie')
        if  cookie != None:
            print('Cookie already exists for user {}.'.format(cookie.get('user_name')))
            overwrite = click.confirm('Overwrite?', default=False)
            if not overwrite:
                return
        cookie = self.get_user_cookie()
        if cookie == None:
            print('Failed to get cookies.')
            return
        is_encrypt = click.confirm('Do you want to encrypt cookies before saving?', default=False)
        if is_encrypt:
            password = 'UnUnsend' + self.get_password_ii()
            cookies = {'encrypted': True, 'user_name': cookie.get('user_name'), 'value': self.encrypt_cookies(cookie.get('cookie'), password)}
        else:
            cookies = {'encrypted': False, 'user_name': cookie.get('user_name') , 'value': cookie.get('cookie')}
        self.__dbms.update_website_stuff('cookie', cookies)

    def configure_ua(self):
        ua = UAGetter().get()
        if not ua:
            print('Unable to get User-Agent.\n')
            return
        print(f'Got User-Agent: {ua}\n')
        self.__dbms.update_website_stuff('user_agent', ua)
    
    def is_valid_url(self, url):
        if not url:
            return False
        try:
            urllib.parse.urlparse(url)
            return True
        except:
            return False

    def configure_discord_hook(self):
        discord = self.__dbms.get_website_stuff('discord')
        if  discord != None:
            print('Discord notification is already configured.')
            overwrite = click.confirm('Overwrite?', default=False)
            if not overwrite:
                return
        while True:
            url = input('Enter discord hook URL: ').strip()
            if self.is_valid_url(url):
                break
            print('Invalid URL.')
        self.__dbms.update_website_stuff('discord', url)
        
    def configure_discord_all_msg(self):
        discord = self.__dbms.get_website_stuff('discord_all_message')
        if  discord != None:
            print('Discord all message notification is already configured.')
            overwrite = click.confirm('Overwrite?', default=False)
            if not overwrite:
                return
        while True:
            url = input('Enter discord hook URL: ').strip()
            if self.is_valid_url(url):
                break
            print('Invalid URL.')
        self.__dbms.update_website_stuff('discord_all_message', url)

    def configure_cleanup(self):
        while True:
            max_message_age = get_int('Max message age (hours)', 36)
            cleanup_interval = get_int('Cleanup interval (hours)', 4)
            if cleanup_interval > max_message_age:
                print('Cleanup interval can not be higher than max message age.\nTry again.')
            else:
                break
        self.__dbms.update_website_stuff('max_message_age', max_message_age)
        self.__dbms.update_website_stuff('cleanup_interval', cleanup_interval)

    def configure_keep_alive_get_uids(self):
        url0 = get_mbasic_link(input('Enter profile link of a friend: ').strip())
        url1 = get_mbasic_link(input('Enter profile link of another friend: ').strip())
        cookies = self.__dbms.get_website_stuff('cookie')
        if not cookies:
            print('Cookie is not configured. Unable to configure keep alive.')
            return
        if cookies.get('encrypted'):
            cookies = decrypt_cookies(cookies.get('value'), getpass.getpass('Cookie is encrypted.\n Enter password: ').strip())
            if not cookies:
                return
        else:
            cookies = cookies.get('value')
        uids = []
        print('Please wait...')
        for url in [url0, url1]:
            try:
                uids.append(self.id_u(requests.get(url, cookies=cookies).text).strip())
            except:
                print('Something went wrong. Please try again.')
                return
        return uids, cookies

    def configure_keep_alive_get_thread_id(self, uids, cookies, inital_msg):
        try:
            client = fbchat.Client(None, None, session_cookies=cookies, user_agent=self.__dbms.get_website_stuff('user_agent'))
            return client.createGroup(inital_msg, uids), client
        except:
            print('Something went wrong. Please try again.')

    def configure_keep_alive(self):
        print('To keep ununsend from getting disconnected, it needs to send messages regularly. To do that, you need to provide profile links of two of your friends. Ununsend will create a group with them and remove them from the group immediately. Then Ununend will use the group to send messages to keep it alive.')
        c = click.confirm('Continue?', default=True)
        initial_msg = 'An automated group.'
        msg = input(f'Enter a group initial message (defaut: {initial_msg}): ').strip()
        
        if not c:
            return
            
        uid_cookies = self.configure_keep_alive_get_uids()
        
        if not uid_cookies:
            return
        
        uids, cookies = uid_cookies
        initial_msg = msg if msg else initial_msg
        thread_id_client = self.configure_keep_alive_get_thread_id(uids, cookies, initial_msg)
        
        if not thread_id_client:
            return
        thread_id, client = thread_id_client
        self.__dbms.update_website_stuff('keep_alive_thread', thread_id)
        print(f'{colors.green}Keep alive thread created successfully.{colors.end}')

        rename = True
        for i in uids:
            try:
                client.removeUserFromGroup(i, thread_id)
            except:
                rename = False
                print(f'{colors.yellow}Warning:{colors.end} Unable to remove user id {i} from group. Please remove manually.')
        if rename:
            try:
                client.changeThreadTitle('Ununsend Keep-Alive', thread_id, fbchat.ThreadType.GROUP)
            except:
                print(f'{colors.yellow}Warning:{colors.end} Failed to rename thread. Please rename manually.')
        try:
            client.muteThread(thread_id=thread_id)
        except:
            print(f'{colors.yellow}Warning:{colors.end} Failed to mute thread. Please mute manually.') 
        try:
            client.changeGroupImageRemote('https://i.imgur.com/b0RhVfN.png',thread_id=thread_id)
        except:
            pass

    def configure_timezone(self):
        tz = self.__dbms.get_website_stuff('timezone')
        if  tz != None:
            print(f'Timezone has already configured as {tz}.')
            overwrite = click.confirm('Overwrite?', default=False)
            if not overwrite:
                return
        while True:
            try:
                cc = input('Enter ISO Alpha-2 country code: ',).strip()
                if len(pytz.country_timezones(cc)) > 0:
                    break
            except KeyboardInterrupt:
                raise
            except:
                pass
            print('Invalid country code.\nSee https://wikipedia.org/wiki/List_of_ISO_3166_country_codes for details.')
        
        while True:
            for i, tz in enumerate(pytz.country_timezones(cc), start=1):
                print(f'\t{i}. {tz}')
            try:
                choice = int(input('Choose a timezone: ')) - 1
                tz = pytz.country_timezones(cc)[choice]
                break
            except KeyboardInterrupt:
                raise
            except:
                print('Invalid Choice. Try again.')
        
        self.__dbms.update_website_stuff('timezone', tz)

    def configure(self):
        c = click.confirm('Configure cookies?', default=True)
        if c:
            self.configure_cookie()
        c = click.confirm('Configure User-Agent (highly recommended)?', default=True)
        if c:
            self.configure_ua()
        c = click.confirm('Configure keep alive (highly recommended)?', default=True)
        if c:
            self.configure_keep_alive()
        c = click.confirm('Configure timezone (highly recommended)?', default=True)
        if c:
            self.configure_timezone()
        c = click.confirm('Configure discord unsent notification?', default=True)
        if c:
            self.configure_discord_hook()
        c = click.confirm('Configure discord all message notification?', default=True)
        if c:
            self.configure_discord_all_msg()
        c = click.confirm('Configure max message age and cleanup interval?', default=True)
        if c:
            self.configure_cleanup()
