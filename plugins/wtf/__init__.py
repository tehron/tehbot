import plugins
import urllib
import lxml.html
import shlex

parser = plugins.ThrowingArgumentParser(
    prog="wtf",
    description="Looks up definitions in Urban Dictionary")
parser.add_argument("search_term")
parser.add_argument("-n", "--nr", help="request definition number NR")

def extract_text(e, xpath):
    e = e.xpath(xpath)
    if not e:
        return ""
    s = e[0].text_content()
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.strip();
    #s = s.encode("utf-8")
    return s

def wtf(connection, channel, nick, cmd, args):
    index = 0
    try:
        pargs = parser.parse_args(shlex.split(args or ""))
        if parser.help_requested:
            return plugins.say(connection, channel, parser.format_help().strip())
        if pargs.nr:
            index = int(pargs.nr) - 1
    except plugins.ArgumentParserError as e:
        return plugins.say(connection, channel, "error: %s" % str(e))
    except (SystemExit, NameError, ValueError):
        return plugins.print_help(connection, channel, nick, None, cmd)
    
    page = index / 7 + 1
    index %= 7
    term = pargs.search_term

    """
    if term.lower() == "maddinw":
        return plugins.say(channel, "A guy commonly referred to as Strong Mad.")
    elif term.lower() == "dloser":
        return plugins.say(channel, "<Jhype> dloser: a thoughtful friend ")
    """

    tree = lxml.html.parse("http://www.urbandictionary.com/define.php?term=%s&page=%d" % (urllib.quote_plus(term.encode("utf-8")), page))
    entries = tree.xpath("//div[@class='def-panel' and @data-defid]")
    txt = "\x0303[Urban Dictionary]\x03 "

    if not entries:
        return plugins.say(connection, channel, txt + "No definition available")

    if index >= len(entries) or index < 0:
        return plugins.say(connection, channel, txt + "No definition nr %d available" % (index + 1))

    count = "?"
    count_div = tree.xpath("//div[contains(@class, 'definition-count-panel')]")
    if count_div:
        try:
            count = str(1 + int(count_div[0].text_content().split()[0]))
        except Exception as e:
            print e
            pass

    txt += "%s (%d/%s)\n" % (term, index + 1, count)
    definition = extract_text(entries[index], ".//div[@class='meaning']")
    txt += plugins.shorten(definition, 300)
    
    example = extract_text(entries[index], ".//div[@class='example']")
    if example:
        txt += "\n\x02Example:\x0f " + plugins.shorten(example, 300)

    plugins.say(connection, channel, txt)

plugins.register_pub_cmd("wtf", wtf)
plugins.register_pub_cmd("define", wtf)
