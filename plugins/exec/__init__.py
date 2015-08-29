import plugins
from os.path import normpath, join, basename
from subprocess import Popen, PIPE

cwd = "/home/tehron"
files = {
    "" : {
        "etc" : {
            "passwd" : "root:x:0:0:root:/root:/bin/bash\ntehron:x:1000:1000:,,,:/home/tehron:/bin/tehsh",
            "shadow" : "root:.EdrlxzlxY4gk:12823:0:99999:7:::\ntehron:$6$f3CDMcXw$LUzSAK/sghqxNeNKcccKKiThZb9C/cyYaUkjvXjnfCsLS8Wf1zIj9Tivai9PmdmkJ8vQ7sxdaUnXW7e..aEtN1:15997:0:99999:7:::"
        },
        "home" : {
            "tehron" : {
                "challs" : {
                    "revolutionelite" : {
                        "solutions.txt" : "Master password is                                                                                                                                                                                                                                                                                                                                                                                                                                        Gx3H,*93nfi.EOF",
                        ".solutions.txt.swp" : "Master password is Gx3H,*93nfi."
                    }
                },
                "tehbot" : {
                    "tehbot.py" : open("tehbot.py").read(),
                    "plugins" : {
                        "__init__.py" : open("plugins/__init__.py").read()
                    }
                },
                ".dloser-mail.tmp" : "Dear dloser -- I love you"
            }
        },
        "bin" : {
            "ls" : "[garbage]",
            "cat" : "[garbage]",
            "tehsh" : "[garbage]",
            "bash": "[garbage]",
            "head" : "[garbage]",
            #"rm" : "[garbage]",
            "uptime" : "[garbage]",
            "uname" : "[garbage]",
            "free" : "[garbage]"
        }
    }
}

def execute(arr):
    return "\n".join(Popen(arr, stdout=PIPE).communicate()[0].splitlines())

def treeget(f):
    comps = normpath(join(cwd, f)).replace("\\", "/").split("/")
    if comps == ["", ""]: comps = [""]
    print comps
    if not comps: return False, None
    tree = files
    for comp in comps:
        if not tree.has_key(comp): return False, None
        tree = tree[comp]
    return True, tree

def ls(args):
    lsfiles = []
    eoa = False
    p_long = False
    p_all = False

    while args:
        a = args.pop(0)
        if a == "--":
            while args:
                lsfiles.append(args.pop(0))
            break
        if a[:1] == "--":
            p = a[2:]
            if p == "all":
                p_all = True
            elif p == "long":
                p_long = True
            else:
                return "ls: Unknown option: --%s" %p
        elif a[0] == "-":
            for p in a[1:]:
                if p == "l":
                    p_long = True
                elif p == "a":
                    p_all = True
                else:
                    return "ls: Unknown option: -%s" %p
        else:
            lsfiles.append(a)

    if not lsfiles:
        lsfiles.append(".")

    print lsfiles
    print p_long, p_all

    res = []
    for f in lsfiles:
        exists, cont = treeget(f)
        print f, (exists, cont)
        if not exists:
            return "ls: %s: No such file or directory" % f
        if isinstance(cont, dict):
            if p_all:
                res.append(".")
                res.append("..")
            for k in cont.keys():
                if k.startswith(".") and not p_all:
                    continue
                if p_long:
                    l = 0 if isinstance(cont[k], dict) else len(cont[k])
                    res.append("%s %d" % (k, l))
                else:
                    res.append(k)
        else:
            if basename(f).startswith(".") and not p_all:
                continue
            if p_long:
                res.append("%s %d" % (f, 0 if cont is None else len(cont)))
            else:
                res.append(f)
    res.sort()
    if p_long:
        res = "\n".join(res)
    else:
        res = " ".join(res)

    return res

def cat(args):
    catfiles = []

    while args:
        a = args.pop(0)
        if a == "--":
            while args:
                catfiles.append(args.pop(0))
            break
        if a[:1] == "--":
            p = a[2:]
            return "cat: Unknown option: --%s" % p
        elif a[0] == "-":
            for p in a[1:]:
                return "cat: Unknown option: -%s" % p
        else:
            catfiles.append(a)
    print catfiles
    if not catfiles:
        return "cat: Missing file argument"

    res = []
    for f in catfiles:
        exists, cont = treeget(f)
        if not exists:
            return "cat: %s: No such file or directory" % f
        if isinstance(cont, dict):
            return "cat: %s: Is a directory" % f
        res.append(cont)

    return "\n".join(res)

def head(args):
    catfiles = []

    lines = 20
    while args:
        a = args.pop(0)
        if a == "--":
            while args:
                catfiles.append(args.pop(0))
            break
        if a[:2] == "--":
            p = a[2:]
            return "head: Unknown option: --%s" % p
        elif a[0] == "-":
            if a[1:].isdigit():
                lines = int(a[1:])
            else:
                for p in a[1:]:
                    if p == "n":
                        if a[2:].isdigit():
                            lines = int(a[2:])
                            break
                        elif not args:
                            return "head: Option requires an argument: -%s" % p
                        else:
                            a2 = args.pop(0)
                            if not a2.isdigit():
                                return "head: %2: Invalid number of lines" % a2
                            lines = int(a2)
                    else:
                        return "head: Unknown option: -%s" % p
        else:
            catfiles.append(a)
    print catfiles
    if not catfiles:
        return "head: Missing file argument"

    res = []
    for f in catfiles:
        exists, cont = treeget(f)
        if not exists:
            return "head: %s: No such file or directory" % f
        if isinstance(cont, dict):
            return "head: %s: Is a directory" % f
        res.append("\n".join(cont.split("\n")[:lines]))

    return "\n".join(res)

def exec_(connection, channel, nick, cmd, args):
    """"""
    if not args: return
    args = args.encode("utf-8")
    args = map(str.strip, args.strip().split())
    cmd = args[0]

    if cmd[0] != "/":
        cmd = normpath(join("/bin", cmd))
        cmd = cmd.replace("\\", "/")

    res = "-tehsh: %s: Command not found" % args[0]
    if cmd == "/bin/ls":
        res = ls(args[1:])
    elif cmd == "/bin/head":
        res = head(args[1:])
    elif cmd == "/bin/cat":
        res = cat(args[1:])
    elif cmd == "/bin/uptime":
        res = execute(["uptime"])
    elif cmd == "/bin/uname":
        res = execute(["uname"] + args[1:])
    elif cmd == "/bin/free":
        res = execute(["free"])
    elif cmd == "/bin/tehsh":
        res = "-tehsh: No cando"
    elif cmd == "/bin/bash":
        res = "-tehsh: No, I like tehsh."

    plugins.say_nick(connection, channel, nick, res)

plugins.register_pub_cmd("exec", exec_)
