#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2012 Collabora Ltd
# Copyright (C) 2012 Luis de Bethencourt <luis.debethencourt@collabora.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
# USA

"""Lucien class"""

from gi.repository import Gst, GstPbutils
from gi.repository import GObject

import os
import sqlite3

class Lucien (GObject.GObject):
    '''Lucien class. Encapsulates all the indexing work in
       simple function per feature for the HMI'''

    __gsignals__ = {
        'discovered': (GObject.SIGNAL_RUN_FIRST, None,
                      (GObject.TYPE_STRING, GObject.TYPE_STRING, \
                       GObject.TYPE_STRING, GObject.TYPE_STRING, \
                       GObject.TYPE_UINT))
    }

    def __init__ (self, standalone=False):
        self.standalone = standalone

        GObject.GObject.__init__(self)
        Gst.init(None)

        self.sqlconn = sqlite3.connect('test.db')
        with self.sqlconn:
            self.sqlcur = self.sqlconn.cursor()
            self.sqlcur.execute('SELECT SQLITE_VERSION()')

            data = self.sqlcur.fetchone()
            print "SQLite version: %s" % data

        self.index = []

    def generate_db (self, folder):
        print "Generating database"
        self.sqlcur.execute("DROP TABLE IF EXISTS Music")
        self.sqlcur.execute("CREATE TABLE Music" + \
                            "(Id INTEGER PRIMARY KEY AUTOINCREMENT, " + \
                            "Artist TEXT, Album TEXT, Title TEXT, " + \
                            "Track INT, Uri TEXT)")
        self.populate_db (folder)

    def scan_folder_for_ext (self, folder, ext):
        for path, dirs, files in os.walk (folder):
            for file in files:
                if file.split('.')[-1] in ext:
                    location = os.path.join(path, file)
                    self.discover_metadata(location)

    def populate_db (self, folder):
        self.scan_folder_for_ext (folder, "mp3")
        self.scan_folder_for_ext (folder, "ogg")
        self.scan_folder_for_ext (folder, "oga")
        self.sqlconn.commit()

    def collect_db (self):
        self.sqlcur.execute('SELECT * from Music')
        music = self.sqlcur.fetchall()
        return music

    def discover_metadata (self, location):
        file_uri= Gst.filename_to_uri (location)
        if not self.standalone:
            info = self.disc.discover_uri_async (file_uri)
        else:
            disc = GstPbutils.Discoverer.new (50000000000)
            info = disc.discover_uri (file_uri)
            tags = info.get_tags ()

            artist = album = title = "unknown"
            track = 0
            tagged, tag = tags.get_string('artist')
            if tagged:
                artist = tag
                artist = unicode(artist, "UTF-8")
            tagged, tag = tags.get_string('album')
            if tagged:
                album = tag
                album = unicode(album, "UTF-8")
            tagged, tag = tags.get_string('title')
            if tagged:
                title = tag
                title = unicode(title, "UTF-8")
            tagged, tag = tags.get_uint('track-number')
            if tagged:
                track = tag

            # print "> %s >> %s >>> %s > %s" % (artist, album, track, title)
            self.sqlcur.execute("INSERT INTO Music VALUES(NULL, " + \
                                "?, ?, ?, ?, ?)", \
                                (artist, album, title, track, file_uri))

    def discovered (self, discoverer, info, error):
        if not error:
            uri = info.get_uri()
            tags = info.get_tags ()

            artist = album = title = "unknown"
            track = 0

            tagged, tag = tags.get_string('artist')
            if tagged:
                artist = tag

            tagged, tag = tags.get_string('album')
            if tagged:
                album = tag

            tagged, tag = tags.get_string('title')
            if tagged:
                title = tag

            tagged, tag = tags.get_uint('track-number')
            if tagged:
                track = tag

        self.emit ("discovered", uri, artist, album, title, track)
        self.index.append((uri, artist, album, title, track))

    def search_in_any (self, query):
        result = []
        for track in self.index:
            if query.lower() in track[1].lower() or \
                    query.lower() in track[2].lower() or \
                    query.lower() in track[3].lower():
                result.append(track)
        return result

    def test (self):
        for t in self.collect_db ():
            print t


if __name__ == "__main__":
    import os, optparse

    usage = """lucien.py -i [folder]"""

    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-i", "--input", action="store", type="string", \
        dest="input", help="Input music file", default="")
    parser.add_option("-d", "--generate-db", action="store_true", \
        dest="gen_db", help="Generate database", default=False)
    (options, args) = parser.parse_args()

    lucien = Lucien(standalone=True)

    if options.gen_db:
        print "Indexing: %r" % options.input
        lucien.generate_db(options.input)
    lucien.test ()
