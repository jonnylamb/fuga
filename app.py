import os
from ConfigParser import ConfigParser

from gi.repository import Gtk, GLib, Gio

import ant.fs.file

import style
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
        self.connect('shutdown', self.shutdown_cb)

        self.config = self.create_config()

        style.setup()

    def activate_cb(self, data=None):
        if 'FAKE_GARMIN' in os.environ:
            g = FakeGarmin()
        else:
            g = Garmin()

        # TODO: so much
        def status_changed_cb(garmin, status):
            print 'new status:', status
        g.connect('status-changed', status_changed_cb)

        def file_list_downloaded_cb(garmin):
            ant_files = garmin.files
            activities = ant_files[ant.fs.file.File.Identifier.ACTIVITY]
            window = Window(self.config)

            for activity in activities:
                window.add_activity(activity)

            self.add_window(window)
            window.show_all()
        g.connect('file-list-downloaded', file_list_downloaded_cb)

        g.start()

        self.garmin = g

    def shutdown_cb(self, app):
        self.garmin.disconnect()

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
