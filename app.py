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

import ant.fs.file

import ui.style
from ui.activities import Activities, ActivitiesHeader
from ui.loading import Loading, LoadingHeader
from ui.welcome import Welcome, WelcomeHeader
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

class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self)

        self.app = app

        self.set_default_size(1000, 700)
        self.set_title('Correre')

        self.stack = Gtk.Stack()
        self.add(self.stack)

        self.pages = (('welcome', Welcome, WelcomeHeader),
                      ('loading', Loading, LoadingHeader),
                      ('activities', Activities, ActivitiesHeader))

        for name, page_type, _ in self.pages:
            self.stack.add_named(page_type(app), name)

        self.current_page = -1
        self.next_page()

    def next_page(self):
        self.current_page += 1
        return self.show_page(self.current_page)

    def first_page(self):
        self.current_page = 0
        return self.show_page(self.current_page)

    def show_page(self, current):
        page_name, _, header_type = self.pages[current]
        page = self.stack.get_child_by_name(page_name)

        old_child = self.stack.get_visible_child()

        page.show_all()
        self.stack.set_visible_child_full(page_name,
            Gtk.StackTransitionType.SLIDE_LEFT)

        if old_child:
            old_child.hide()

        header = header_type()
        header.show_all()
        self.set_titlebar(header)

        # welcome page
        if hasattr(header, 'close_button'):
            header.close_button.connect('clicked', lambda x: self.destroy())

        # welcome page
        if hasattr(header, 'next_button'):
            header.next_button.connect('clicked', self.next_clicked_cb)

        # activities page
        if hasattr(header, 'back_button'):
            header.back_button.connect('clicked', self.back_clicked_cb)
        if hasattr(page, 'set_header'):
            page.set_header(header)

        return page

    def next_clicked_cb(self, button):
        self.next_page()
        self.app.queue.get_file_list(self.get_file_list_cb)

    def get_file_list_cb(self, ant_files):
        page = self.next_page()

        for activity in ant_files[ant.fs.file.File.Identifier.ACTIVITY]:
            page.add_activity(activity)
        page.select_first()
        page.show_all()

    def back_clicked_cb(self, button):
        self.first_page()

        # destroy activities, for good luck
        self.stack.remove(self.stack.get_child_by_name('activities'))
        self.stack.add_named(Activities(self.app), 'activities')
