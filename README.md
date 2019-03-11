# tehbot
A Python IRC Bot

## Installation
* Install Python >= 2.7.10 with pip
* Run `pip install --upgrade irc lxml tmdbsimple wolframalpha prettytable psutil pony`
* Checkout the source to `$TEHBOTDIR`

## Running
* `cd $TEHBOTDIR`
* `python -m tehbot`

## Interacting with tehbot
Tehbot has an active command line which accepts the following commands (commands have to be preceded with a slash `/`):
* `reload` -- reloads all plugins and applies all changes made to tehbot's connections
* `quit` -- quits tehbot (optional arguments are supplied as quit message)
* `stats` -- shows some statistics about connected networks' status and period command plugins
* `config` -- edit or show tehbot's settings

## Configuration

### Global Configuration
* `/config tehbot modify set botname "mytehbot"` -- set tehbot's name to `mytehbot`
* `/config tehbot modify set cmdprefix "!"` -- set tehbot's command prefix to `!` (tehbot will react to IRC messages that start with `!`)
* `/config tehbot connections add "IRC Network"` -- add an IRC network tehbot should connect to as "IRC Network"
  * `/config tehbot connections modify "IRC Network" set host "irc.network.org"`
  * `/config tehbot connections modify "IRC Network" set port 7000`
  * `/config tehbot connections modify "IRC Network" set ssl "True"`
  * `/config tehbot connections modify "IRC Network" add channels "#channel1"`
  * `/config tehbot connections modify "IRC Network" add channels "#channel2"`
  * `/config tehbot connections modify "IRC Network" add operators "your_nickserv_regged_nick"`
  
  Optionally:
  * `/config tehbot connections modify "IRC Network" set botname "tehnetworkbot"` -- set a network specific name tehbot should use
  * `/config tehbot connections modify "IRC Network" set password "********"` -- set a NICKSERV password tehbot should use to authenticate
  * `/config tehbot connections modify "IRC Network" set id "net"` -- set a unique id for a network

### Plugin Configuration
...
