from gi.repository import Gtk, GLib, Gio

from activities import Window

class Run(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self, application_id='com.jonnylamb.Run',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)

        GLib.set_application_name('Run')

        self.connect('activate', self.activate_cb)

    def activate_cb(self, data=None):
        window = Window()
        self.add_window(window)

        window.show_all()
