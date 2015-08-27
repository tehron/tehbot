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

    count = "?"
    count_div = tree.xpath("//div[contains(@class, 'definition-count-panel')]")
    if count_div:
        try:
            count = str(1 + int(count_div[0].text_content().split()[0]))
        except Exception as e:
            print e
            pass

    txt = "\x02[Definition 1/%s]\x0f " % count
    definition = extract_text(entries[index], ".//div[@class='meaning']")
    if len(definition) > 300:
        definition = definition[:300] + "..."
    txt += definition
    
    plugins.say(connection, channel, definition)

    example = extract_text(entries[index], ".//div[@class='example']")
    if example:
        if len(example) > 300:
            example = example[:300] + "..."
        txt += "\n\x02Example:\x0f " + example

    plugins.say(connection, channel, txt)

plugins.register_pub_cmd("wtf", wtf)
plugins.register_pub_cmd("define", wtf)
