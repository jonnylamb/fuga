# Copyright (C) 2015 Jonny Lamb <jonnylamb@jonnylamb.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
from ConfigParser import ConfigParser

from gi.repository import Gtk, GLib, Gio, Gdk

import ui.style
from ui.window import Window
from fakegarmin import FakeGarmin
from garmin import Garmin
from devicequeue import GarminQueue

CONFIG_PATH = os.path.join(GLib.get_user_config_dir(), 'fuga', 'fuga.ini')

class Fuga(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self, application_id='com.jonnylamb.Fuga',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)

        GLib.set_application_name('Fuga')

        self.connect('activate', self.activate_cb)

        self.config = self.create_config()

        ui.style.setup()

        if 'FAKE_GARMIN' in os.environ:
            cls = FakeGarmin
        else:
            cls = Garmin

        self.queue = GarminQueue(cls)

    def activate_cb(self, data=None):
        window = Window(self)
        self.add_window(window)
        window.show_all()

        window.connect('destroy', self.window_destroy_cb)
        window.connect('key-press-event', self.key_press_event_cb)

    def window_destroy_cb(self, window):
        self.queue.shutdown()

    def key_press_event_cb(self, window, event):
        if (event.state & Gdk.ModifierType.CONTROL_MASK \
            and event.keyval == Gdk.KEY_q) or \
           event.keyval == Gdk.KEY_Escape:
            window.destroy()

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
            os.chmod(CONFIG_PATH, 0600)
        config.save = save_config

        return config
