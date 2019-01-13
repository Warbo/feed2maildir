from __future__ import print_function

import datetime
import hashlib
import json
import os
import random
import sys
import time

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
            for l in sorted(self.links.keys()):
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
        self.delivered = 0

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
        new = []

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
                h.update(post[k].encode('utf-8'))
                data[k] = h.hexdigest()
        return "SEP".join([k + "PES" + data[k] for k in sorted(data.keys())])

    def check_maildir(self, maildir):
        """Check access to the maildir and try to create it if not present"""
        mdirs = ('', '/tmp', '/new', '/cur')
        for mdir in mdirs:
            fullname = maildir + mdir
            if not os.access(fullname, os.W_OK):
                try: # to make the maildirs
                    os.makedirs(fullname)
                except:
                    sys.exit('ERROR: accessing "{}" failed'.format(fullname))

        hashes = []
        # Run a few times, to reduce the chance of missing something
        for iteration in [0, 1, 2]:
            # Look up all message filenames. These won't change, but they
            # may be moved from 'new' to 'cur' while we're running.
            messages = []
            for subdir in ['new', 'cur']:
                messages += os.listdir(os.path.join(maildir, subdir))
            for messagefile in list(set(messages)):
                # Look up the location of each message on demand, to prevent
                # our listings going stale
                foundfile = False
                for subdir in ['new', 'cur']:
                    try:
                        with open(os.path.join(maildir,
                                               subdir,
                                               messagefile),
                                  'r') as message:
                            foundfile = True
                            found = [l for l in message.readlines()
                                     if l.startswith('X-feed2maildirsimple-hash')]
                            if found != []:
                                hashes.append(found[0].split(' ')[1])
                    except IOError:
                        # We only expect one to be found
                        pass
                if not foundfile:
                    print("WARNING: couldn't find {} in {}".format(
                        messagefile,
                        self.name))
            time.sleep(1)
        return list(set(hashes))

    def compose(self, post):
        """Compose the mail using the tempate"""
        try: # to get the update/publish time from the post
            updated = post.updated
        except: # the property is not set, use now()
            updated = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
        desc = ''
        if self.strip:
            stripper = HTMLStripper()
            stripper.feed(post.description)
            desc = stripper.get_data()
        else:
            desc = post.description
        return self.TEMPLATE.format(updated, post.title, self.name,
                                    self.make_hash(post), post.link, desc)

    def write(self, message):
        """Take a message and write it to a mail"""
        rand = random.randint(0,0xFFFFFFFF)
        dt = time.time()
        ticks = int((dt - int(dt)) * 1000000)
        pid = str(os.getpid())
        host = os.uname()[1]
        self.delivered += 1
        name = u'{}/new/{}.M{}R{:08x}Q{}P{}.{}'.format(self.maildir, int(dt), ticks, rand, self.delivered, pid, host)
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
