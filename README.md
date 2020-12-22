# tehbot
A Python IRC Bot

## Installation
* Install Python >= 3.7, incl. pip
* Install dependencies:
  * MySQL driver:
     * If your Linux Distro has a working MySQLdb module for Python 3 (Debian 10 (buster) e.g.): run `sudo apt install python3-mysqldb`
     * Else run `sudo pip3 install --upgrade PyMySQL`
  * Run `sudo pip3 install --upgrade irc lxml tmdbsimple wolframalpha prettytable psutil pony requests`
* Checkout the source to `$TEHBOTDIR`

## Running
* `cd $TEHBOTDIR`
* `python3 -m tehbot`

## Interacting with tehbot
Tehbot has a command line interface which accepts the following commands:
* `reload` -- reloads all plugins and applies all changes made to tehbot's connections
* `quit` -- quits tehbot (optional arguments are supplied as quit message)
* `stats` -- shows some statistics about connected networks' status and period command plugins
* `config` -- edit or show tehbot's settings

## Configuration

### Global Configuration
* `config global set botname "mytehbot"` -- set tehbot's name to `mytehbot`
* `config global set ircname "mytehbot"` -- set tehbot's irc name to `mytehbot`
* `config global set username "mytehbot"` -- set tehbot's user name to `mytehbot`
* `config global set cmdprefix "!"` -- set tehbot's command prefix to `!` (tehbot will react to IRC messages that start with `!`)
* `config global add connection ircnet irc.network.org 7000` -- add ircnet as IRC network tehbot should connect to

### IRC Network Configuration
* `config connection ircnet set ssl "True"`
* `config connection ircnet add channels #channel1`
* `config connection ircnet add channels #channel2`channelkey
* `config connection ircnet add operators your_nickserv_regged_nick1`
* `config connection ircnet add operators your_nickserv_regged_nick2`

Optionally:
* `config connection ircnet set botname "tehnetworkbot"` -- set a network specific name tehbot should use
* `config connection ircnet set password "********"` -- set a NICKSERV password tehbot should use to authenticate
* `config connection ircnet set host "irc.network.org"`
* `config connection ircnet set port 7000`

### Channel Configuration
* `config channel ircnet #channel1 set password "********"` -- set channel password for this channel
* `config channel ircnet #channel1 set logging False` -- turn off logging for this channel

### Plugin Configuration
* `config plugin PingPlugin set enabled True`
...
