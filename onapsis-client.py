#!/usr/bin/python
import requests
import readline
import cmd
import re
import json
import getpass
import bs4
import time

try:
    from termcolor import colored
except ImportError:
    def colored(text, color=None, bgColor=None, attrs=None):
        return text

class OnapsisShellPrompt:
    def __init__(self):
        self.level = '0'

    def __str__(self):
        return self.getTime() + ' ' + self.getBold('$') + ' '


    def getLevel(self):
        return self.getBold('[', 'white') + self.getBold('level ' + self.level, 'blue') + self.getBold(']', 'white')

    def getBold(self, char, color=None):
        return colored(char, color, attrs=['bold'])

    def getTime(self):
        return self.getBold('[', 'green') + colored(time.strftime('%H:%M:%S'), 'green') + self.getBold(']', 'green')

    def setLevel(self, level):
        self.level = level

class OnapsisShell(cmd.Cmd, object):
    def __init__(self):
        super(OnapsisShell, self).__init__()
        self.loggedIn = False
        self.prompt = OnapsisShellPrompt()
        self.game = OnapsisGame()
        self.readConfig()

    def cmdloop(self):
        print(colored(' --! Onapsis Adventure !-- ', 'red', 'on_white', attrs=['bold']))
        try:
            if self.config.get('autologin'):
                self.autologin()
        except:
            print ('')
            pass
        alive = True
        while alive:
            try:
                alive = super(OnapsisShell, self).cmdloop()
            except KeyboardInterrupt:
                print("^C")

    def readConfig(self):
        try:
            self.config = json.loads(open('onapsis-client.config', 'r').read())
        except:
            self.config = dict()

    def autologin(self):
        if self.config.get('username') and self.config.get('password'):
            self.login(self.config.get('username'), self.config.get('password'))
        elif self.config.get('username'):
            print("Auto Login")
            self.do_login(self.config.get('username'))
        else:
            self.echoError('Username not configured')

    def login(self, username, password):
        self.game.login(username, password)
        self.echo(self.game.getInitialContext())
        self.loggedIn = True

    def formatLevelTitle(self, matches):
        return colored(matches.group(0), 'blue', 'on_white', attrs=['bold'])

    def formatLevelPrompt(self, matches):
        return colored(matches.group(0), 'white', attrs=['bold'])

    def echo(self, text):
        levels = re.findall(r'#### YOU ARE NOW PLAYING LEVEL ([0-9]+) ####', text)
        if levels:
            self.prompt.setLevel(levels[-1])
        text = re.sub(r'\n#### .+\n', self.formatLevelTitle, text, flags=re.MULTILINE)
        text = re.sub(r'^\$.+$', self.formatLevelPrompt, text, flags=re.MULTILINE)
        print(text)
        self.log('output: %s' % text)

    def echoError(self, text):
        return self.echo(colored(text, 'red', attrs=['bold']))

    def log(self, text):
        f = open('./onapsis-client.log', 'a')
        f.write(time.strftime('[%Y-%m-%d %H:%M:%S] ') + text + '\n')
        f.close()

    def precmd(self, line):
        self.log('cmd: %s' % line)
        return line

    def default(self, line):
        if not self.loggedIn:
            self.echo("Not logged in.")
            return
        result = self.game.command(line)
        if not result['success']:
            self.echoError("ERROR executing command: %s" % line)
        if 'output' in result:
            self.echo(result['output'])

    def do_help(self, line):
        self.default('help')

    def do_clear(self, line):
        print (chr(27) + "[2J")

    def do_autologin(self, line):
        self.autologin()

    def do_login(self, username):
        if not username:
            self.echoError("Usage: login <username>")
            return
        password = getpass.getpass()
        if not password:
            self.echoError("Password cannot be empty")
            return
        self.login(username, password)

    def do_logout(self, line):
        self.game.logout()
        self.echo("Logged out.")

    def do_quit(self, line):
        return self.do_exit(line)

    def do_exit(self, line):
        return True

class OnapsisGame:
    def __init__(self):
        self.url = 'https://online.onapsis.com'
        self.session = requests.Session()
        self.initialContext = ''
        self.response = None

    def getInitialContext(self):
        return self.initialContext

    def login(self, username, password):
        # Get main page to set cookies
        self.session.get(self.url)
        data = dict(username=username, password=password)
        self.response = self.session.post(self.url + '/login', data=data, allow_redirects=True)
        match = re.search(r'\<body\>(.*?)\<\/body\>', self.response.content.decode('UTF-8', 'replace'), flags=re.DOTALL)
        self.initialContext = bs4.BeautifulSoup(match.group(1)).getText().strip()

    def logout(self):
        self.session.get(self.url + '/logout')

    def command(self, command):
        data = dict(command=command)
        self.response = self.session.post(self.url + '/command', data=data)
        content = self.response.content.decode('UTF-8', 'replace')
        try:
            return json.loads(content)
        except:
            return dict(success=False, output='Exception getting response: %s' % content)

console = OnapsisShell()
console.cmdloop()

