import plugins
import urllib
import lxml.html

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
    """Usage: ?wtf [nr] term"""
    index = 0
    if not args:
        return plugins.print_help(connection, channel, nick, None, cmd)

    args = args.strip().split()
    if args[0].strip().isdigit():
        index = int(args.pop(0)) - 1

    page = index / 7 + 1
    index %= 7
    term = " ".join(args)

    """
    if term.lower() == "maddinw":
        return plugins.say(channel, "A guy commonly referred to as Strong Mad.")
    elif term.lower() == "dloser":
        return plugins.say(channel, "<Jhype> dloser: a thoughtful friend ")
    """

    tree = lxml.html.parse("http://www.urbandictionary.com/define.php?term=%s&page=%d" % (urllib.quote_plus(term.encode("utf-8")), page))
    entries = tree.xpath("//div[@class='def-panel']")
    if not entries:
        return plugins.say(connection, channel, "'%s' has no definition at http://www.urbandictionary.com" % term)

    if index >= len(entries) or index < 0:
        return plugins.say(connection, channel, "No definition nr %d available" % (index + 1))

    definition = extract_text(entries[index], ".//div[@class='meaning']")
    if len(definition) > 450:
        definition = definition[:450] + "..."
    plugins.say(connection, channel, definition)
    example = extract_text(entries[index], ".//div[@class='example']")
    if example:
        if len(example) > 440:
            example = example[:440] + "..."
        plugins.say(connection, channel, "\x02Example:\x0f " + example)

plugins.register_pub_cmd("wtf", wtf)
