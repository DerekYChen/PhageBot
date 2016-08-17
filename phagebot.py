import argparse
import os
import random
import re
import socket
import time
from mcstatus import MinecraftServer

#command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--debug', help='Runs script in debug mode, on channel #testbot2', action='store_true')
parser.add_argument('--mcserver', help='Hostname/IP of Minecraft server the bot should poll for information')
parser.add_argument('--server', help='Hostname/IP of IRC server the bot should connect to')
args = parser.parse_args()

#config vars
if args.server:
    network = args.server
else:
    print("--server must be set")
    exit()
port = 6667
nick = 'PhageBot'
uname = 'PhageBot'
realname = 'PhageBot'
channel = '#main'
mcserverip = args.mcserver if args.mcserver else -1

logpath = './../.znc/users/derek/moddata/log'
quotepath = './quotes/'

#check if running in debug mode
if args.debug:
    nick = 'PhageBot2'
    uname = 'PhageBot2'
    realname = 'PhageBot2'
    channel = '#testbot2'

    logpath = './fakelogs/'

#other vars
data = ''
lastdata = ''
eightball = [
    'It is decidedly so',
    'Without a doubt',
    'Yes, definitely',
    'Most likely',
    'Signs point to yes',
    'Reply hazy try again',
    'Ask again later',
    'Better not tell you now',
    'Cannot predict now',
    'Concentrate and ask again',
    "Don't count on it",
    'My reply is no',
    'My sources say no',
    'Outlook not so good',
    'Very doubtful'
]
manual = {
    '8ball' : '!8ball - completely accurate fortune telling device',
    'grab' : '!grab - grabs last message sent and stores it for !quote',
    'list' : '!list [num] - displays num-th page of the list of commands, defaults to first page',
    'man' : 'pls',
    'mcstatus' : '!mcstatus - checks online status of phage MC server',
    'quote' : '!quote [name] - returns random stored quote of [name], random stored quote if name empty',
    'random' : '!random - spits out a "random" quote from logs of #main',
    'rtd' : '!rtd [num1]d[num2] - simulates rolling a num2-face die num1 times. defaults to 1d20'
}

#helper functions
def findcommand(command):
    if data.startswith('!' + 'PhageBot'): return False
    datasplit = data.split(channel + ' :')
    return datasplit[1].startswith(command + '\r\n') or datasplit[1].startswith(command + ' ') if len(datasplit) > 1 else False

def splitmsg(command):
    datasplit = data.split(command + ' ')
    if len(datasplit) > 1:
        return datasplit[1].strip()
    else:
        return ''

def sendmsg(msg):
    global data
    msg = str(msg)
    irc.send ("PRIVMSG " + channel + " :" + msg + "\n")
    data = '!' + 'PhageBot' + '@' + channel + ' :' + msg

def rtd(inp):
    try:
    	ans = ''
    	roll = inp.split('d')
    	numrolls = int(roll[0])
    	die = int(roll[1])
    	for i in xrange(0,min(10,numrolls)):
    		ans = ans + str(random.randint(1,die)) + ' '
        return ans
    except (IndexError, ValueError):
        return 'rtfm u fukin tard'

def randomquote():
    logfiles = [f for f in os.listdir(logpath) if '#main' in f]
    logfile = os.path.join(logpath,random.choice(logfiles))
    date = logfile.split('#main_')[1][:8]
    with open(logfile) as f:
        logs = [line.strip() for line in f if line.strip()]
    return date + ' ' + random.choice(logs)

#timezones
os.environ['TZ'] = 'US/Pacific'

# set up socket, join server
irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
irc.connect((network, port))
print irc.recv(4096)
irc.send('NICK ' + nick + '\n')
irc.send('USER ' + uname + ' 2 3 ' + realname + '\n')

#build !list
commands = ['!' + command for command in list(manual.keys())]
perpage = 10
listpages = [' '.join(commands[i:i+perpage]) for i in xrange(0,len(commands),perpage)]

#init mc server
mcserver = MinecraftServer.lookup(mcserverip)

#main loop
while True:
    if args.debug and data:
        print data
    lastdata = data
    data = irc.recv(4096)
    if 'End of message of the day' in data:
        irc.send('JOIN ' + channel + '\n')
        print 'Trying to join server'
        irc.send('OPER PhageBot myopiceps' + "\n")
    if 'End of /NAMES list' in data:
        sendmsg('v1.7.0')
    if 'PING' in data:
        irc.send('PONG ' + data.split()[1] + '\n')
    if findcommand('!8ball'):
        sendmsg(random.choice(eightball))
    if findcommand('!grab'):
        datetime = time.strftime('%Y-%m-%d [%H:%M:%S]', time.localtime(time.time()+205))
        name = re.search('!(.*)@', lastdata).group(1)
        msg = lastdata.split(channel + ' :')[1].strip()
        if name not in ['Derek','Kevin','PhageBot']:
            name = 'Nerd'
        quote = datetime + ' <' + name + '> ' + msg
        sendmsg('Grabbed ' + quote)
        with open(quotepath + name + '.txt','a+') as f:
            f.write(quote+'\n')
    if findcommand('!list'):
        page = splitmsg('!list')
        if page:
            try:
                pagenum = int(page)
                sendmsg('page [' + page + '/' + str(len(listpages)) + ']: ' + listpages[pagenum-1])
            except IndexError:
                sendmsg('page ' + page + ' does not exist')
            except ValueError:
                sendmsg(page + ' is not a page number man')
        else:
            sendmsg('page [1/' + str(len(listpages)) +']: ' + listpages[0])
    if findcommand('!man'):
        cmd = splitmsg('!man').strip()
        if not cmd:
            sendmsg("did you really search for the manual of nothing")
        elif cmd in manual:
            sendmsg(manual[cmd])
        else:
            sendmsg("the fuck is " + cmd)
    if findcommand('!mcstatus'):
        if mcserverip != -1:
            try:
                numplayers = mcserver.status().players.online
                if (numplayers > 0):
                    sendmsg("currently online: {0}".format(", ".join(mcserver.query().players.names)))
                else:
                    sendmsg("no one is online")
            except IOError:
                sendmsg('could not connect to mc server')
        else:
            sendmsg("no MC server ip during config")
    if findcommand('!quote'):
        name = splitmsg('!quote')
        if not name:
            quotefiles = [f for f in os.listdir(quotepath) if not f.startswith('.')]
            if quotefiles:
                quotefile = os.path.join(quotepath, random.choice(quotefiles))
            else:
                sendmsg('no stored quotes m8')
                continue
        elif name in ['Derek','Kevin','Nerd','PhageBot']:
            quotefile = os.path.join(quotepath, name + '.txt')
        else:
            sendmsg('who the fuck is ' + name)
            continue
        try:
            with open(quotefile) as f:
                quotes = [line.strip() for line in f if line.strip()]
            sendmsg(random.choice(quotes))
        except IOError:
            sendmsg('no fukn quotes for ' + name + ' yet')
    if findcommand('!rtd'):
        inp = splitmsg('!rtd')
        sendmsg(rtd(inp)) if inp else sendmsg(rtd('1d20'))
    if findcommand('!random'):
        sendmsg(randomquote())
