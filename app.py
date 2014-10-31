import os
from ConfigParser import ConfigParser

from gi.repository import Gtk, GLib, Gio

import ant.fs.file

import style
from activities import Activities, ActivitiesHeader
from loading import LoadingWindow
from fakegarmin import FakeGarmin
from garmin import Garmin
from queue import GarminQueue

CONFIG_PATH = os.path.join(GLib.get_user_config_dir(), 'correre', 'correre.ini')

class Correre(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self, application_id='com.jonnylamb.Correre',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)

        GLib.set_application_name('Correre')

        self.connect('activate', self.activate_cb)

        self.config = self.create_config()

        style.setup()

        if 'FAKE_GARMIN' in os.environ:
            cls = FakeGarmin
        else:
            cls = Garmin

        self.queue = GarminQueue(cls)

    def activate_cb(self, data=None):
        self.loading = LoadingWindow(self)
        self.add_window(self.loading)
        self.loading.show_all()

        self.queue.get_file_list(self.got_file_list_cb)

    def got_file_list_cb(self, ant_files):
        self.loading.destroy()
        self.loading = None

        activities = ant_files[ant.fs.file.File.Identifier.ACTIVITY]
        window = Window(self)

        for activity in activities:
            window.activities.add_activity(activity)

        self.add_window(window)
        window.show_all()

        window.connect('destroy', self.window_destroy_cb)

    def window_destroy_cb(self, window):
        self.queue.shutdown()

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

class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self)

        self.app = app

        self.set_default_size(1000, 700)
        self.set_title('Correre')

        # titlebar
        self.header = ActivitiesHeader()
        self.set_titlebar(self.header)

        self.activities = Activities(app)
        self.activities.set_header(self.header)
        self.add(self.activities)
