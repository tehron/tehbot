# tehbot
A Python IRC Bot

## Installation
* Install Python >= 2.7.10 with pip
* Run `pip install --upgrade irc lxml tmdbsimple wolframalpha prettytable psutil pony enum34 python-dateutil`
* Checkout the source to `$TEHBOTDIR`

## Running
* `cd $TEHBOTDIR`
* `python -m tehbot`

## Interacting with tehbot
Tehbot has a command line interface which accepts the following commands:
* `reload` -- reloads all plugins and applies all changes made to tehbot's connections
* `quit` -- quits tehbot (optional arguments are supplied as quit message)
* `stats` -- shows some statistics about connected networks' status and period command plugins
* `config` -- edit or show tehbot's settings

## Configuration

### Global Configuration
* `config global set botname "mytehbot"` -- set tehbot's name to `mytehbot`
* `config global set cmdprefix "!"` -- set tehbot's command prefix to `!` (tehbot will react to IRC messages that start with `!`)
* `config global add connection ircnet irc.network.org 7000` -- add ircnet as IRC network tehbot should connect to
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

* `config channel ircnet #channel1 set logging False` -- turn off logging for this channel

### Plugin Configuration
* `config plugin PingPlugin set enabled True`
...
