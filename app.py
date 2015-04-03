import os
from ConfigParser import ConfigParser

from gi.repository import Gtk, GLib, Gio, Gdk

import ant.fs.file

import style
from activities import Activities, ActivitiesHeader
from loading import Loading, LoadingHeader
from welcome import Welcome, WelcomeHeader
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

        self.pages = {'welcome': Welcome(app),
                      'loading': Loading(app),
                      'activities': Activities(app)}

        for name, page in self.pages.items():
            self.stack.add_named(page, name)

        self.show_welcome()

    # welcome page

    def show_welcome(self):
        page = self.pages['welcome']
        page.show_all()
        self.stack.set_visible_child_full('welcome',
            Gtk.StackTransitionType.SLIDE_RIGHT)

        header = WelcomeHeader()
        header.show_all()
        self.set_titlebar(header)

        header.close_button.connect('clicked', self.welcome_close_clicked_cb)
        header.next_button.connect('clicked', self.welcome_next_clicked_cb)

    def welcome_close_clicked_cb(self, button):
        self.destroy()

    def welcome_next_clicked_cb(self, button):
        self.show_loading()
        self.app.queue.get_file_list(self.got_file_list_cb)

    # loading page

    def show_loading(self):
        page = self.pages['loading']
        page.show_all()
        self.stack.set_visible_child_full('loading',
            Gtk.StackTransitionType.SLIDE_LEFT)

        header = LoadingHeader()
        header.show_all()
        self.set_titlebar(header)

        header.prev_button.connect('clicked', self.loading_prev_clicked_cb)

    def loading_prev_clicked_cb(self, button):
        self.show_welcome()

    def got_file_list_cb(self, ant_files):
        self.show_activities()

        page = self.pages['activities']
        for activity in ant_files[ant.fs.file.File.Identifier.ACTIVITY]:
            page.add_activity(activity)
        page.select_first()
        page.show_all()

    # activities page

    def show_activities(self):
        page = self.pages['activities']

        header = ActivitiesHeader()
        page.set_header(header)
        header.show_all()
        self.set_titlebar(header)

        page.show_all()
        self.stack.set_visible_child_full('activities',
            Gtk.StackTransitionType.SLIDE_LEFT)

        header.back_button.connect('clicked', self.activities_back_clicked_cb)

    def activities_back_clicked_cb(self, button):
        self.show_welcome()

        # destroy activities, for good luck
        self.stack.remove(self.pages['activities'])
        self.pages['activities'] = Activities(self.app)
        self.stack.add_named(self.pages['activities'], 'activities')
