import datetime
import hashlib
import json
import os
import random
import sys

if sys.version[0] == '2':
    from HTMLParser import HTMLParser
else:
    from html.parser import HTMLParser

import dateutil.parser

# Python 2.x compabitlity
if sys.version[0] == '2':
    FileNotFoundError = IOError

class HTMLStripper(HTMLParser):
    """Strips HTML off an string"""
    def __init__(self):
        self.reset()
        self.strict = False
        self.fed = []
        self.convert_charrefs = True
        self.numlinks = 0
        self.links = {}

    def handle_data(self, d):
        self.fed.append(d)

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            for attr in attrs:
                if attr[0] == 'src':
                    link = attr[1]
                    break;
            self.fed.append('[Image]: {}\n'.format(link))
        elif tag == 'a':
            for attr in attrs:
                if attr[0] == 'href':
                    self.links[self.numlinks] = attr[1]
        elif tag == 'li':
            self.fed.append('- ')

    def handle_endtag(self, tag):
        if tag == 'a':
            self.fed.append(' [{}]'.format(self.numlinks))
            self.numlinks += 1

    def get_data(self):
        out = ''.join(self.fed)
        if self.numlinks:
            out += '\n'
            for l in range(self.numlinks):
                out += '  [{}]: {}\n'.format(l, self.links[l])
        return out

class Converter:
    """Converts new entries to maildir"""

    TEMPLATE = u"""MIME-Version: 1.0
Date: {}
Subject: {}
From: {}
Content-Type: text/plain
X-feed2maildirsimple-hash: {}

Link: {}

{}
"""

    def __init__(self, maildir, name, strip=False, silent=False):
        self.name    = name
        self.silent  = silent
        self.maildir = os.path.expanduser(maildir)
        self.strip   = strip
        if self.strip:
            self.stripper = HTMLStripper()

    def run(self):
        """Do a full run"""
        if self.feed:
            hashes = self.check_maildir(self.maildir)
            self.news = self.find_new(self.feed, hashes)
            for newpost in self.news:
                self.write(self.compose(newpost))

    def load(self, feed):
        """Load a feed"""
        self.feed = feed

    def find_new(self, feed, hashes):
        """Find the new posts by comparing them to the found hashes"""
        new      = []

        for post in feed.entries:
            # See if we've already got a message for this item
            h       = self.make_hash(post)
            matches = [x for x in hashes if self.hashes_match(h, x)]
            if matches == []:
                new.append(post)
        return new

    def hashes_match(self, x, y):
        """Check if the data in two hashes match"""
        x_bits = [bit.split("PES") for bit in x.split("SEP")]
        y_bits = [bit.split("PES") for bit in y.split("SEP")]

        x_data = {}
        for k, v in x_bits:
            x_data[k] = v.strip()
        y_data = {}
        for k, v in y_bits:
            y_data[k] = v.strip()

        mismatch = False
        for k in x_data:
            if k in y_data:
                if x_data[k] != y_data[k]:
                    mismatch = True
        for k in y_data:
            if k in x_data:
                if x_data[k] != y_data[k]:
                    mismatch = True

        return (not mismatch)

    def make_hash(self, post):
        """Make an identifying hash for this post"""
        data = {"feed": self.name}
        for k in ["id", "title", "ppg_canonical", "link", "author"]:
            if k in post:
                h = hashlib.sha256()
                h.update(post[k])
                data[k] = h.hexdigest()
        return "SEP".join([k + "PES" + data[k] for k in sorted(data.keys())])

    def check_maildir(self, maildir):
        """Check access to the maildir and try to create it if not present"""
        mdirs = ('', '/tmp', '/new', '/cur')
        for mdir in mdirs:
            fullname = maildir + mdir
            if not os.access(fullname, os.W_OK):
                try: # to make the maildirs
                    os.mkdir(fullname)
                except:
                    sys.exit('ERROR: accessing "{}" failed'.format(fullname))

        hashes = []
        for folder, subs, files in os.walk(maildir):
            for filename in files:
                with open(os.path.join(folder, filename), 'r') as message:
                    found = [l for l in message.readlines()
                             if l.startswith('X-feed2maildirsimple-hash')]
                    if found != []:
                        hashes.append(found[0].split(' ')[1])
        return hashes

    def compose(self, post):
        """Compose the mail using the tempate"""
        try: # to get the update/publish time from the post
            updated = post.updated
        except: # the property is not set, use now()
            updated = datetime.datetime.now()
        desc = ''
        if self.strip:
            self.stripper.feed(post.description)
            desc = stripper.get_data()
        else:
            desc = post.description
        return self.TEMPLATE.format(updated, post.title, self.name,
                                    self.make_hash(post), post.link, desc)

    def write(self, message):
        """Take a message and write it to a mail"""
        rand = str(random.randint(10000, 99999))
        dt = str(datetime.datetime.now())
        pid = str(os.getpid())
        host = os.uname()[1]
        name = u'{}/new/{}{}{}{}'.format(self.maildir, rand, dt, pid, host)
        try: # to write out the message
            with open(name, 'w') as f:
                # We can thank the P2/P3 unicode madness for this...
                if sys.version[0] == '2':
                    f.write(str(message.encode('utf8')))
                else:
                    f.write(message)
        except:
            self.output('WARNING: failed to write message to file')

    def mktime(self, arg):
        """Make a datetime object from a time string"""
        return dateutil.parser.parse(arg)

    def output(self, arg):
        if not self.silent:
            print(arg)
