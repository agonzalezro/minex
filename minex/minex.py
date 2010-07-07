#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement
import gtk
import sys
import gtkmozembed
import os
from pysqlite2 import dbapi2 as sqlite
import ConfigParser
import re
# To get_favicon
import shutil
import urllib2
import lxml.html

import gtk.glade
import subprocess

import gettext
APP="minex"  
POPATH="po"
gettext.textdomain(APP)  
gettext.bindtextdomain(APP, POPATH)
gtk.glade.textdomain(APP)  
gtk.glade.bindtextdomain(APP, POPATH)
gettext.install('py-gtkshots', 'po', True)
_ = gettext.gettext


XMLPATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../debian/minex/usr/share/minex/ui/minex.xml')
ICONPATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/minex.png')
TMPDIR = '/tmp/minex'

class Layout:
    program_path = None

    def __init__(self, file, window, program_path, home = None):
        self.program_path = program_path

        config = Config()
        self.moz = dict()
        self.moz[0] = gtkmozembed.MozEmbed()
        if not os.path.exists(TMPDIR): os.mkdir(TMPDIR)

        self.builder = gtk.Builder()
        self.builder.add_from_file(file)
        window = self.builder.get_object(window)

        home = self.initialize_mozilla(self.moz[0], config, home)
        self['tabs'].append_page(self.moz[0])

        self.resize_window(window, config)
        self.moz[0].show()
        window.show()

        # I must do this here, because if I initialize database after load_url, it doesn't work
        self.fill_combo(self['url'], home)

        self.e = Event(self)
        self.builder.connect_signals(self.e)
        self.moz[0].connect('location', self.e.on_location_changed)
        self.moz[0].connect('title', self.e.on_title_changed)
        self.moz[0].connect('progress', self.e.on_progress_changed)

        self.moz[0].connect('dom_mouse_click', self.e.button_press_over_link)
        self.moz[0].connect('net_start', self.e.net_start_event)

    def add_new_mozilla(self, page):
        self.moz[page] = gtkmozembed.MozEmbed()
        self.moz[page].show()
        self.moz[page].connect('location', self.e.on_location_changed)
        self.moz[page].connect('title', self.e.on_title_changed)
        self.moz[page].connect('progress', self.e.on_progress_changed)

        self.moz[page].connect('dom_mouse_click', self.e.button_press_over_link)
        self.moz[page].connect('net_start', self.e.net_start_event)

        return self.moz[page]

    def initialize_mozilla(self, mozilla, config, home = None):
        if not home:
            try:
                home = config['home']
            except:
                home = 'about:blank'

        mozilla.load_url(home)
        return home

    def resize_window(self, window, config):
        if config['width'] != None and config['width'] != "-1": width = int(config['width'])
        else: width = 640

        if config['height'] != None and config['height'] != "-1": height = int(config['height'])
        else: height = 480

        window.set_default_size(width, height)

    def fill_combo(self, combo, actual, needed_search = False):
        database = DataBase()
        if not needed_search:
            self.set_model_from_list(combo, database.get_only_five(actual))
            combo.set_active(0)
        else:
            # The string actual is the key to the search too
            self.set_model_from_list(combo, database.get_only_five(actual, actual))

    def __getitem__(self, key):
        return self.builder.get_object(key)

    def set_model_from_list (self, cb, items):
        """Setup a ComboBox or ComboBoxEntry based on a list of strings."""
        model = gtk.ListStore(str)
        for i in items:
            model.append([i])
        cb.set_model(model)
        if type(cb) == gtk.ComboBoxEntry:
            cb.set_text_column(0)
        elif type(cb) == gtk.ComboBox:
            cell = gtk.CellRendererText()
            cb.pack_start(cell, True)
            cb.add_attribute(cell, 'text', 0)

    def get_favicon(self, url, path='/tmp/favicon.ico', alt_icon_path=ICONPATH):
        """ Some code of this function from: http://code.activestate.com/recipes/577114-downloading-websites-favicon/ """
        if url.startswith("about:"): return alt_icon_path

        HEADERS = {
            'User-Agent': 'urllib2 (Python %s)' % sys.version.split()[0],
            'Connection': 'close',
        }

        url = re.search('(http(s)?://)?.*(\.[a-z][a-z][a-z]?)', url).group(0) + '/'
        if (not url.startswith('http://')) and (not url.startswith('https://')): url = 'http://' + url

        # Create files for all favicon's in /tmp... for cache and for concurrence between the future tabs or several minex opened
        path = os.path.join(TMPDIR, url[0:-1].replace('http://', '').replace('.', '_') + '.ico')

        if os.path.exists(path): return path

        request = urllib2.Request(url + 'favicon.ico', headers=HEADERS)
        try:
            icon = urllib2.urlopen(request).read()
        except(urllib2.HTTPError, urllib2.URLError):
            reqest = urllib2.Request(url, headers=HEADERS)
            try:
                content = urllib2.urlopen(request).read(2048) # 2048 bytes should be enought for most of websites
            except(urllib2.HTTPError, urllib2.URLError):
                shutil.copyfile(alt_icon_path, path)
                return
            icon_path = lxml.html.fromstring(x).xpath(
                '//link[@rel="icon" or @rel="shortcut icon"]/@href'
            )
            if icon_path:
                request = urllib2.Request(url + icon_path[:1], headers=HEADERS)
                try:
                    icon = urllib2.urlopen(request).read()
                except(urllib2.HTTPError, urllib2.URLError):
                    shutil.copyfile(alt_icon_path, path)
                    return
        try:
            open(path, 'wb').write(icon)
        except:
            return

        return path

    def delete_moz_and_reorder(self, page):
        for i in range(page, len(self.moz)):
            if (i+1 < len(self.moz)):
                self.moz[i] = self.moz[i+1]


class Event:
    combo_length = 0
    first_time = True
    no_size = False
    control = False
    last_link = None
    page = 0
    clicked = False

    def __init__(self, parent):
        self.parent = parent
        self.database = DataBase()
        self.config = Config()
        self.page  = int(parent['tabs'].get_current_page())

    def button_press_over_link(self, widget, event):
        # FIXME: do this only in right-click, but I don't know how to cast gpointer to gtk.gdk.Event to get the event.button
        if widget.get_link_message():
            self.last_link = widget.get_link_message()
            self.parent['moz_menu'].popup(None, None, None, 3, 0)

    # I can't stop the signal emmited to load a page when I click in a link, so I must do it at this way
    def net_start_event(self, widget):
        if widget.get_link_message() and not self.clicked:
            widget.stop_load()
        else:
            self.clicked = False

    def on_open_here_click(self, widget):
        self.clicked = True
        self.parent.moz[self.page].load_url(self.last_link)

    def on_open_in_tab_click(self, widget):
        page = self.on_add_tab_clicked(widget)
        self.clicked = True
        self.parent.moz[page].load_url(self.last_link)

    def on_open_in_window_click(self, widget):
        program = "%s %s \"%s\"" % ("python", self.parent.program_path, self.last_link)
        subprocess.Popen(program, shell=True)

    def on_tabs_switch_page(self, widget, page, page_num):
        self.page = int(page_num)
        self.load_web_info(self.parent.moz[self.page])

    def on_button_press_event(self, widget, event):
        self.page = widget.get_current_page()
        if event.button == 3:
            widget.emit_stop_by_name('button_press_event')
            self.parent['tabs_menu'].popup(None, None, None, event.button, event.time)

    def on_add_tab_clicked(self, widget):
        new_page_num = self.parent['tabs'].get_n_pages()
        moz = self.parent.add_new_mozilla(new_page_num)
        self.parent['tabs'].append_page(moz)
        self.parent['tabs'].set_current_page(new_page_num)
        self.parent['main'].set_focus(self.parent['url'])

        return new_page_num
    
    def on_delete_tab_clicked(self, widget):
        self.parent.delete_moz_and_reorder(self.page)
        self.parent['tabs'].remove_page(self.page)

    def on_location_changed(self, widget):
        pass

    def on_title_changed(self, widget):
        if widget.get_title():
            self.parent['tabs'].set_tab_label_text(widget, widget.get_title())
            self.parent['main'].set_title(widget.get_title() + _(' - minino explorer'))
        # I usually loads the web from progess, but if I can't determine if the web is loaded or no, I must do this
        if self.no_size:
            self.load_web_info(widget)
            self.no_size = False

    def on_progress_changed(self, widget, current, length):
        if length == -1: self.no_size = True

        if current == length:
            self.load_web_info(widget)

    def load_web_info(self, widget):
        if widget.get_title():
            self.parent['tabs'].set_tab_label_text(widget, widget.get_title())
            self.parent['main'].set_title(widget.get_title() + _(' - minino explorer'))
        self.parent['back'].set_sensitive(widget.can_go_back())
        self.parent['forward'].set_sensitive(widget.can_go_forward())
        if widget.get_link_message():
            # self.parent['url'].set_text(self.parent.moz.get_link_message())
            self.parent.fill_combo(self.parent['url'], widget.get_link_message(), True)
            self.parent['url'].set_active(0)
            self.database.save_as_history_entry(widget.get_link_message())
        else:
            if (widget.get_location()): self.parent.fill_combo(self.parent['url'], widget.get_location(), False)
            self.database.save_as_history_entry(self.parent['url'].get_active_text())

        icon_path = self.parent.get_favicon(self.parent['url'].get_active_text())
        try:
            icon = gtk.gdk.pixbuf_new_from_file(icon_path)
            self.parent['main'].set_icon(icon)
        except:
            # This could fail if the icon isn't retrieved at time
            pass

    def on_back_clicked(self, widget):
        self.parent.moz[self.page].go_back()
        self.load_web_info(widget)

    def on_forward_clicked(self, widget):
        self.parent.moz[self.page].go_forward()
        self.load_web_info(widget)

    def on_home_clicked(self, widget):
        self.parent.moz[self.page].load_url(self.config['home'])
        self.parent.fill_combo(self.parent['url'], self.config['home'], False)
        self.parent['url'].set_active(0)
        self.load_web_info(self.parent.moz[self.page])

    def on_refresh_clicked(self, widget):
        self.parent.moz[self.page].reload(gtkmozembed.FLAG_RELOADNORMAL)

    def on_history_clicked(self, widget):
        database = DataBase()
        data = database.get_history()
        self.parent.moz[self.page].render_data(data, long(len(data)), 'file:///', 'text/html')

    def on_url_changed(self, widget):
        # BAD: We've made a click (or paste) because I can't write (or erase) two letter at same time
        # I can erase more than a letter at time, but not paste it
        if len(widget.get_active_text()) - self.combo_length >= 2:
            self.parent.moz[self.page].load_url(widget.get_active_text())
            #self.parent.set_model_from_list(widget, self.database.get_only_five(widget.get_active_text(), widget.get_active_text()))
            self.parent.fill_combo(widget, widget.get_active_text(), True)
        self.combo_length = len(widget.get_active_text())

    def on_main_key_press_event(self, widget, key):
        if key.keyval == 65507: self.control = True
    
    def on_main_key_release_event(self, widget, key):
        # <Ctrl> + T
        if key.keyval == 116 and self.control:
            self.on_add_tab_clicked(self.parent['tabs'])

        if key.keyval == 65507: self.control = False

    def on_url_key_release_event(self, widget, key):
        # This is the return key (I must compare this with a CONST from keymap and not whit a numeric value)
        if key.keyval == 65293: # Return key
            # This is a fucking "bug", if I'm on about:blank and try to load a webpage, I need to load it (or press enter) two times
            if self.first_time:
                self.parent.moz[self.page].load_url(widget.get_active_text())
                self.first_time = None
            self.parent.moz[self.page].load_url(widget.get_active_text())
        else:
            if len(widget.get_active_text()) >= 3:
               self.parent.set_model_from_list(widget, self.database.get_only_five(widget.get_active_text(), widget.get_active_text()))
               self.parent.fill_combo(widget, widget.get_active_text(), True)
    
    def on_url_key_press_event(self, widget, key):
        if key.keyval == 65364: # Down key
            widget.popup()
            widget.stop_emission('key-press-event')
        elif key.keyval == 65289: # Tab key
            self.parent['search'].set_sensitive(True)
            self.parent['search_container'].set_focus_child(self.parent['search'])
            self.parent['main'].set_focus_child(self.parent['search_container'])
            widget.stop_emission('key-press-event')

    def on_search_activate(self, widget):
        self.parent.moz[self.page].load_url(self.config['search_uri'] + widget.get_text())

    def on_main_destroy(self, widget):
        (_, _, self.config['width'], _) = self.parent['main'].get_allocation()
        (_, _, _, self.config['height']) = self.parent['main'].get_allocation()
        # Remove temp files
        try:
            for file in os.listdir(TMPDIR):
                os.remove(os.path.join(TMPDIR, file))
            os.rmdir(TMPDIR)
        except:
            pass
        gtk.main_quit()


class DataBase:
    dir_path = os.environ['HOME'] + '/.minex/'
    file_path = dir_path + 'minex.db'
    connection = None;
    cursor = None;

    def __init__(self):
        if not os.path.exists(self.file_path):
            if not os.path.exists(self.dir_path): os.mkdir(self.dir_path)
            self.create_database()
        else:
            self.connection = sqlite.connect(self.file_path)
            self.cursor = self.connection.cursor()

    def create_database(self):
        self.connection = sqlite.connect(self.file_path)
        self.cursor = self.connection.cursor()

        try:
            self.cursor.execute('CREATE TABLE history (url VARCHAR(1024) PRIMARY KEY, time DATETIME);')
            self.connection.commit()
        except:
            print 'Error writing table history in ' + file_path + ', try rm -rf ' + file_path

        try:
            self.cursor.execute('CREATE TABLE bookmarks (url VARCHAR(1024));')
            self.connection.commit()
        except:
            print 'Error writing table bookmarks in ' + file_path + ', try rm -rf ' + file_path

    def save_as_history_entry(self, url):
        if (self.sanitize(url)):
            sql = 'REPLACE INTO history (url, time) VALUES (?, DATETIME("NOW"));'
            self.cursor.execute(sql, (self.sanitize(url), ))
            self.connection.commit()

    def save_as_bookmark_entry(self, url):
        if (self.sanitize(url)):
            sql = 'REPLACE INTO bookmarks (url) VALUES (?);'
            self.cursor.execute(sql, (self.sanitize(url), ))
            self.connection.commit()

    def get_history(self):
        data = '<html><head><title>History</title></head><body><h1>History</h1><ul>'

        for row in self.cursor.execute('SELECT * FROM history;'):
            data = data + '<li><a href="http://%s">%s</a> (%s)</li>' % (row[0], row[0], row[1])

        data = data + '</body></html>'
        return data

    def get_only_five(self, actual, key = None):
        items = list()
        items.append(actual)

        if key: sql = 'SELECT * FROM history WHERE url LIKE \'%' + key + '%\' ORDER by time LIMIT 5;'
        else: sql = 'SELECT url FROM history ORDER by time LIMIT 5;'

        for row in self.cursor.execute(sql):
            items.append(row[0])

        return items

    def sanitize(self, url):
        url = url.lower()

        if url.endswith("/"):
            url = url[0:-1]

        if url.startswith('http://'):
            url = url.split('http://')[1]

        # If starts with http, could starts with www. too, so we need to test it here without elif statement
        if url.startswith('www.'):
            url = url.split('www.')[1]
        elif url.startswith('about:'):
            url = False

        return url



class Config:
    dir_path = os.environ['HOME'] + '/.minex/'
    file_path = dir_path + 'config'
    config = None

    def __init__(self):
        if not os.path.exists(self.file_path):
            if not os.path.exists(self.dir_path): os.mkdir(self.dir_path)
            self.create_config()

        self.config = self.initialize()

    def initialize(self):
        config = ConfigParser.ConfigParser()
        config.readfp(file(self.file_path))
        return config

    def create_config(self):
        try:
            tosave = ConfigParser.RawConfigParser()
            tosave.add_section('general')
            tosave.set('general', 'home', 'about:blank')
            tosave.set('general', 'search_uri', 'http://www.google.es/#q=')
            tosave.set('general', 'width', -1)
            tosave.set('general', 'height', -1)

            with open(self.file_path, 'wb') as configfile:
                tosave.write(configfile)
        except:
            print 'Error writing config in ' + self.file_path + ', try rm -rf ' + self.file_path

    def __getitem__(self, key):
        try:
            return self.config.get('general', key)
        except:
            # It doesn't exist
            return None

    def __setitem__(self, key, value):
        self.config = self.initialize()

        # I'm creating new list, instead use elements_from_file to reuse some code
        elements = list()
        elements_from_file = self.config.items("general")
        i = 0
        while i < len(elements_from_file):
            elements.append(elements_from_file[i][0])
            i=i+1

        try:
            tosave = ConfigParser.RawConfigParser()
            tosave.add_section('general')

            for element in elements:
                if element != key:
                    if self[key]: tosave.set('general', element, self[element])
                else:
                    tosave.set('general', key, value)

            with open(self.file_path, 'wb') as configfile:
                tosave.write(configfile)
        except:
            print 'Error saving element ' + key + ' in config file ' + self.file_path + ', try rm -rf ' + self.file_path


if __name__ == '__main__':
    home = None
    if len(sys.argv) > 1: home = sys.argv[1]

    Layout(XMLPATH, window='main', program_path=os.path.abspath(sys.argv[0]), home=home)
    gtk.main()
