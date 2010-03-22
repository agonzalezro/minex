#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gtk
import sys
import gtkmozembed
import os
from pysqlite2 import dbapi2 as sqlite
import ConfigParser


class Layout:
    def __init__(self, file, window, home = None):
        config = Config()
        self.moz = gtkmozembed.MozEmbed()
        
        self.builder = gtk.Builder()
        self.builder.add_from_file(file)
        self.window = self.builder.get_object(window)
        try:
            self.window.set_size_request(int(config['width']), int(config['height']))
        except:
            pass
        
        self['vbox1'].pack_start(self.moz)
        self.moz.show()
        
        if not home:
            try:
                home = config['home']
            except:
                home = 'about:blank'

        self['url'].set_text(home)
        self.moz.load_url(home)
        self['url'].select_region(0, -1)
        self.window.show()

        e = Event(self)
        self.builder.connect_signals(e)
        self.moz.connect('location', e.on_location_changed)
        self.moz.connect('title', e.on_title_changed)
        

    def __getitem__(self, key):
        return self.builder.get_object(key)


class Event:
    def __init__(self, parent):
        self.parent = parent
        self.database = DataBase()
        self.first_time = True
        
    def on_location_changed(self, widget):
        pass
        
    def on_title_changed(self, widget):
        if self.parent.moz.get_title():
            self.parent['main'].set_title(self.parent.moz.get_title() + ' - minino explorer')
        self.parent['back'].set_sensitive(self.parent.moz.can_go_back())
        self.parent['forward'].set_sensitive(self.parent.moz.can_go_forward())
        if self.parent.moz.get_link_message():
            self.parent['url'].set_text(self.parent.moz.get_link_message())
            self.database.save_as_history_entry(self.parent.moz.get_link_message())
        else:
            self.database.save_as_history_entry(self.parent['url'].get_text())        

    def on_back_clicked(self, widget):
        self.parent.moz.go_back()

    def on_forward_clicked(self, widget):
        self.parent.moz.go_forward()
    
    def on_home_clicked(self, widget):
        config = Config()
        self.parent.moz.load_url(config['home'])
        #FIXME: This event doesn't change the home page
    
    def on_refresh_clicked(self, widget):
        self.parent.moz.reload(gtkmozembed.FLAG_RELOADNORMAL)
        
    def on_history_clicked(self, widget):
        database = DataBase()
        data = database.get_history()
        self.parent.moz.render_data(data, long(len(data)), 'file:///', 'text/html')

    def on_url_activate(self, widget):
        #FIXME: This is a fucking bug, if I'm on about:blank and try to load a webpage, I need to load it (or press enter) two times
        if self.first_time:
            self.parent.moz.load_url(self.parent['url'].get_text())
            self.first_time = None
        self.parent.moz.load_url(self.parent['url'].get_text())
        
    def on_url_insert_text(self, widget, new, length, position):
        #This is to show the history
        pass
        
    def on_search_activate(self, widget):
        config = Config()
        self.parent.moz.load_url(config['search_uri'] + self.parent['search'].get_text())   

    def on_main_destroy(self, widget):
        Config()
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
    
    def sanitize(self, url):
        url = url.lower()
        
        if url.endswith("/"):
            url = url[0:-1]
        
        if url.startswith('http://'):
            url = url.split('http://')[1]
        
        #If starts with http, could starts with www. too, so we need to test it here without elif statement
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
            
        self.config = ConfigParser.ConfigParser()
        self.config.readfp(file(self.file_path))
            
    def create_config(self):
        try:
            f = open(self.file_path, "w");
            f.write("[general]\nhome = about:blank\nsearch_uri = http://www.google.es/#q=")
            f.close()
        except:
            print 'Error writing config in ' + file_path + ', try rm -rf ' + file_path
        
    def __getitem__(self, key):
        return self.config.get('general', key)
    

if __name__ == '__main__':
    home = None
    if len(sys.argv) > 1: home = sys.argv[1]
         
    Layout('minex.xml', 'main', home)
    gtk.main()
