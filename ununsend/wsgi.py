from flask import Flask, render_template
from flask import request as flask_request
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_login import login_user, login_required, current_user
from fbchat import FBchatUserError
import time
import string
import random
import threading
import json
import functools
import getpass
import os

from . import ununsend_client
from .dbms import DBMS
from . import utils
from . import __static_path, __template_path

ALWAYS_ACTIVE = False
CLEANUP_INTERVAL = 4 # Hours
MAX_MESSAGE_AGE = 36 # Hours

app = Flask(__name__, template_folder=os.path.expanduser(__template_path), static_folder=os.path.expanduser(__static_path))
login_manager = LoginManager(app)
socketio = SocketIO(app)
dbms = None
clients = []

def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            pass #do nothing
        else:
            return f(*args, **kwargs)
    return wrapped

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html'), 401

@login_manager.user_loader
def load_user(user_id):
    return dbms.get_website_user(user_id)

@socketio.on('client_connected')
@authenticated_only
def handle_client_connected(json_data):
    clients.append(flask_request.sid)
    try:
        currently_have = json.loads(json_data)['currently_have']
    except:
        currently_have = 0
    
    if currently_have != 0:
        return
    
    initial_message = dbms.unsentManager.get_all() # should not case a problem as unsent messages are not that often
    notif_texts = [ununsend_client.make_notification_text_from_obj(i) for i in initial_message]
    utils.update_on_website(socketio, notif_texts, flask_request.sid)

@app.route('/')
@login_required
def home():
    return render_template('list.html')

@app.route('/auth')
def auth_user():
    token = flask_request.args.get('token')
    if not token:
        return 'Bad requests', 400
    if not dbms.tokenManager.remove_auth_token(token):
        return 'Invalid auth token', 403
    
    login_user(dbms.add_and_get_user(True), True)
    
    return render_template('afterauth.html')

def website_main(active_network=False, port=5000, print_info=[], dbms_parm=None):
    global dbms
    if dbms_parm == None:
        dbms= DBMS()
    else:
        dbms = dbms_parm
    
    app.config['SECRET_KEY'] = dbms.get_flask_secret()
    run_listener = True
    
    cookies = dbms.get_website_stuff('cookie')
    if not cookies:
        print('Cookie is not configured. Run ununsend -c to configure.')
        print('Without cookies Ununsent can not show unsent messages.')
        run_listener = False
    if cookies and cookies.get('encrypted'):
        dec_cookies = utils.decrypt_cookies(cookies.get('value'), getpass.getpass('Cookie is encrypted.\n Enter password: ').strip())
        if not dec_cookies:
            run_listener = False
        cookies['value'] = dec_cookies
    if run_listener:
        print(f'Found cookie for user: {cookies.get("user_name")}')
        try:
            listener = ununsend_client.Listener(cookies.get('value'), dbms, clients, socketio)
        except:
            print('Failed to login. Please check if the cookie has expired then try again.')
            return
        
        fbchatThread = threading.Thread(target=ununsend_client.main, args=(listener, ALWAYS_ACTIVE))
        fbchatThread.start()
        clearUpThread = threading.Thread(target=utils.clear_up, args=(dbms, CLEANUP_INTERVAL, MAX_MESSAGE_AGE))
        clearUpThread.start()
    
    if active_network:
        host = '0.0.0.0'
    else:
        host = '127.0.0.1'
    utils.print_with_delay(print_info, 5)
    socketio.run(app, host=host, port=f'{port}')

if __name__ == '__main__':
    website_main()
