import os
import time
import json
import psutil
import requests
import click
import base64
from socket import AF_INET
from threading import Thread
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

from . import __debug_discord
from . import colors

# Modified from https://stackoverflow.com/questions/12524994/encrypt-decrypt-using-pycrypto-aes-256 by mnothic
class AESCipher(object):
    def __init__(self, key): 
        self.bs = AES.block_size
        self.key = PBKDF2(key.encode('utf-8'), dkLen=32, salt=b'saltysalt', count=10000)

    def encrypt(self, raw:str):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw.encode())).decode('utf-8')

    def decrypt(self, enc):
        enc = base64.b64decode(enc.encode('utf-8'))
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

class DaemonThread(Thread):
    def __init__(self, func, *args):
        super().__init__(target=func, args=tuple(args))
        self.daemon = True

def clear_up(dbms, cleanupInterval, maxMessageAge):
    while True:
        time.sleep(cleanupInterval * 3600)
        timestamp_filter = int(time.time() * 1000) - maxMessageAge * 3600000
        dbms.unsentManager.clearUp(timestamp_filter)

def update_on_website(socket, notif_texts, client=None):
    if not isinstance(notif_texts, list):
        notif_texts = [notif_texts]
    to_send = []
    for i in notif_texts:
        lines = [j.strip() for j in i.split('\n') if j.strip()]
        to_send.append({'title': lines[0], 'body': lines[1:]})
    if client == None:
        socket.emit('load_messages', json.dumps(to_send))
    else:
        socket.emit('load_messages', json.dumps(to_send), room=client)

def get_if_addrs():
    addrs = []
    for _, v in psutil.net_if_addrs().items():
        if v[0].family == AF_INET:
            addrs.append(v[0].address)
    return addrs  

def mk_website_links(url:str, port, localhost=False) -> list:
    if localhost:
        return [url.replace('__website_home__', f'http://127.0.0.1:{port}')]
    urls = []
    for addr in get_if_addrs():
        urls.append(url.replace('__website_home__', f'http://{addr}:{port}'))
    return urls

def format_token_print(token, port, localhost):
    addition = ' ' if localhost else ' one of '
    strf = f'Please visit{addition}the link below for authentiction.\n\n'
    if localhost:
        strf += f'http://127.0.0.1:{port}/auth?token={token}'
        return strf
    
    for addr in get_if_addrs():
        strf += f'http://{addr}:{port}/auth?token={token}\n'
    return strf.strip()

def print_with_delay(texts, delay):
    def print_with_delay_impl(_texts, _delay):
        if not isinstance(_texts, list):
            _texts = [_texts]
        time.sleep(_delay)
        for i in _texts:
            print(i)
    DaemonThread(print_with_delay_impl, texts, delay).start()

def decrypt_cookies(cookie, password):
    password = 'UnUnsend' + password
    aes = AESCipher(password)
    try:
        return json.loads(aes.decrypt(cookie))
    except:
        print('Something went wrong.')
        print('Check your password and try again.')

def debug_discord(message):
        path = os.path.expanduser(__debug_discord)
        if not os.path.isfile(path):
            return
        with open(path, 'r') as f:
            debug_hook = f.read().strip()
        try:
            requests.post(debug_hook, json={'content': message})
        except:
            print(f'{colors.red}Debug Discord Failed.\nMessage: {message}{colors.end}')
