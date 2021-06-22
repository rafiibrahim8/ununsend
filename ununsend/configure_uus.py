import click
import requests
import json
import urllib
import getpass
import re

from .utils import AESCipher

def get_int(prompt, default):
    while True:
        try:
            return int(click.prompt(prompt, default=f'{default}'))
        except:
            print('Invalid Input. Try again.')

class ConfigureUUS:
    def __init__(self, dbms):
        self.__dbms=dbms
    
    def id_u(self, res_dot_text):
        try:
            return re.findall('<a href=\\"\\/.{1,}\\/about\\?lst=([^%\\"]+)', res_dot_text)[0]
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
                cookie = requests.utils.dict_from_cookiejar(browser(domain_name='messenger.com'))
                user_name = self.check_cookie_whois(cookie)
                if user_name != None:
                    cookies.append({'browser_name': name, 'user_name': user_name, 'cookie': cookie})
            except:
                pass
        return cookies
    
    def get_user_cookie(self):
        print('Checking for messenger profiles on the PC.\nThis may take some time.\nPlease wait...')
        profiles = self.check_for_fb_profile()
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
                user_input = int(user_input)
            except: 
                print('Invalid input.')
                continue
            if user_input > len(profiles) or user_input < 1:
                print('Invalid input.')
                continue
            print(f'Selected profile: {profiles[user_input-1].get("user_name")}')
            cookie = profiles[user_input-1]
            del cookie['browser_name']
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

    def is_valid_url(self, url):
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
        
    def configure_push_bullet(self):
        pb = self.__dbms.get_website_stuff('push_bullet')
        if  pb != None:
            print('Push Bullet notification is already configured.')
            overwrite = click.confirm('Overwrite?', default=False)
            if not overwrite:
                return
        while True:
            token = input('Enter Push Bullet access token: ').strip()
            if token:
                break
            print('Empty token.')
        self.__dbms.update_website_stuff('push_bullet', token)
    

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
    
    def configure(self):
        c = click.confirm('Configure cookies?', default=True)
        if c:
            self.configure_cookie()
        c = click.confirm('Configure discord unsent notification?', default=True)
        if c:
            self.configure_discord_hook()
        c = click.confirm('Configure Push Bullet unsent notification?', default=True)
        if c:
            self.configure_push_bullet()
        c = click.confirm('Configure discord all message notification?', default=True)
        if c:
            self.configure_discord_all_msg()
        c = click.confirm('Configure max message age and cleanup interval?', default=True)
        if c:
            self.configure_cleanup()

