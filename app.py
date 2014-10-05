import os
from ConfigParser import ConfigParser

from gi.repository import Gtk, GLib, Gio

import ant.fs.file

import style
from activities import Window
from loading import LoadingWindow
from fakegarmin import FakeGarmin
from garmin import Garmin

CONFIG_PATH = os.path.join(GLib.get_user_config_dir(), 'correre', 'correre.ini')

class Correre(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self, application_id='com.jonnylamb.Correre',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)

        GLib.set_application_name('Correre')

        self.connect('activate', self.activate_cb)
        self.connect('shutdown', self.shutdown_cb)

        self.config = self.create_config()

        style.setup()

    def got_file_list_cb(self, ant_files):
        self.loading.destroy()
        self.loading = None

        activities = ant_files[ant.fs.file.File.Identifier.ACTIVITY]
        window = Window(self)

        for activity in activities:
            window.add_activity(activity)

        self.add_window(window)
        window.show_all()

    def activate_cb(self, data=None):
        if 'FAKE_GARMIN' in os.environ:
            self.garmin = FakeGarmin()
        else:
            self.garmin = Garmin()

        self.loading = LoadingWindow(self.garmin)
        self.add_window(self.loading)
        self.loading.show_all()

        self.garmin.do(self.garmin.get_file_list, self.got_file_list_cb)

    def shutdown_cb(self, app):
        self.garmin.shutdown()

    def create_config(self):
        path = os.path.dirname(CONFIG_PATH)
        if not os.path.exists(path):
            os.mkdir(path)

        config = ConfigParser()

        if os.path.exists(CONFIG_PATH):
            config.read(CONFIG_PATH)

        def save_config():
            with open(CONFIG_PATH, 'w') as configfile:
                config.write(configfile)
        config.save = save_config

        return config
