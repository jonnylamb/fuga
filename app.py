import os
import pickle
from ConfigParser import ConfigParser

from gi.repository import Gtk, GLib, Gio

import ant.fs.file

from activities import Window
from fakegarmin import FakeGarmin
from garmin import Garmin

CONFIG_PATH = os.path.join(GLib.get_user_config_dir(), 'correre', 'correre.ini')

class Run(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self, application_id='com.jonnylamb.Run',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)

        GLib.set_application_name('Run')

        self.connect('activate', self.activate_cb)

        self.config = self.create_config()

    def activate_cb(self, data=None):
        if 'FAKE_GARMIN' in os.environ:
            g = FakeGarmin()
        else:
            g = Garmin()

        def status_changed(garmin, status):
            print 'new status:', status
        g.connect('status-changed', status_changed)

        def files(garmin, p):
            ant_files = pickle.loads(p)
            activities = ant_files[ant.fs.file.File.Identifier.ACTIVITY]
            window = Window(self.config)

            for activity in activities:
                window.add_activity(activity)

            self.add_window(window)
            window.show_all()
        g.connect('files', files)

        g.start()

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
