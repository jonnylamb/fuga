import os
import pickle

from gi.repository import Gtk, GLib, Gio

import ant.fs.file

from activities import Window
from fakegarmin import FakeGarmin
from garmin import Garmin

class Run(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self, application_id='com.jonnylamb.Run',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)

        GLib.set_application_name('Run')

        self.connect('activate', self.activate_cb)

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
            window = Window()

            for activity in activities:
                window.add_activity(activity)

            self.add_window(window)
            window.show_all()
        g.connect('files', files)

        g.start()
