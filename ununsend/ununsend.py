from argparse import ArgumentParser

from .dbms import DBMS
from .utils import format_token_print
from .wsgi import website_main
from .configure_uus import ConfigureUUS
from . import __version__

class UnunsendMain:
    def __init__(self):
        self.__dbms = DBMS()
    
    def delete_dbms(self):
        del self.__dbms
    
    def run_server(self, active_network, print_info=[]):
        from .wsgi import website_main
        website_main(active_network, self.port, print_info, self.__dbms)        

    def new_token_and_run(self):
        token =  self.__dbms.tokenManager.add_and_get_new_token()
        self.run_server(True, format_token_print(token, self.port, False))

    def get_port(self):
        good_port = True
        try:
            port = int(self.args.port)
            if port < 1025 or port > 65535:
                good_port = False
        except:
            good_port = False
        
        if not good_port:
            print('Invalid port {}'.format(self.args.port))
            print('Defaulting to 5000')
            return '5000'
        return self.args.port.strip()

    def mk_config(self):
        ConfigureUUS(self.__dbms).configure()
    
    def run_on_args(self):
        parser = ArgumentParser(description='View messages that were unsent on Messenger.')
        parser.add_argument("-v", "--version", action="version", version=f"v{__version__}", help="Show version information.")
        mainGroup = parser.add_mutually_exclusive_group()
        mainGroup.add_argument('-D', '--new-device', dest='new_device', action='store_true', help='Authenticate new device/browser.')
        serverGroup = mainGroup.add_mutually_exclusive_group()
        serverGroup.add_argument('-r', '--run-localhost', dest='net_off', action='store_true', help='Run the listener with the server on localhost only (default behaviour).')
        serverGroup.add_argument('-R', '--run-all', dest='net_on', action='store_true', help='Run the listener with the server on all interfaces.')
        mainGroup.add_argument('-c', '--configure', dest='configure', action='store_true', help='Interactively configure the program.')
        parser.add_argument('-p', '--port', dest='port', default='5000', help='Port in which the website will run. Default: 5000')

        args = parser.parse_args()
        self.args = args        
        self.port = self.get_port()

        if args.new_device:
            self.new_token_and_run()
        elif args.net_on:
            self.run_server(True)
        elif args.configure:
            self.mk_config()
        else:
            self.run_server(False)

def main():
    UnunsendMain().run_on_args()

if __name__ == '__main__':
    main()

