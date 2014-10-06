import os
import random
from datetime import datetime

from gi.repository import GLib, GObject

import ant.fs.file

from garmin import Garmin, FILETYPES, AntFile
import utils

class FakeAntFile(object):
    def __init__(self, base_path, name):
        self.filename = name

        date, time, subtype, number = name.split('_')
        self.save_date = datetime.strptime(date + '_' + time, '%Y-%m-%d_%H-%M-%S')

        self.path = os.path.join(base_path, FILETYPES[int(subtype)], self.filename)

class FakeGarmin(GObject.GObject):

    @GObject.Signal(arg_types=(int,))
    def status_changed(self, status):
        pass

    def __init__(self, authentication_fail=False):
        GObject.GObject.__init__(self)

        self.loop = GObject.MainLoop()
        self.status = Garmin.Status.NONE

        self.authentication_fail = authentication_fail
        self.wait_time = int(os.environ.get('FAKE_GARMIN_TIME', 200))

        self.funcs = []

    def change_status(self, status):
        self.status = status
        # run in ui thread
        GLib.idle_add(lambda: self.emit('status-changed', status))

    @utils.run_in_thread
    def start(self):
        self.change_status(Garmin.Status.CONNECTING)

        GLib.timeout_add(self.wait_time, self.authentication_cb)
        self.loop.run()

    def authentication_cb(self):
        self.change_status(Garmin.Status.AUTHENTICATION)

        if self.authentication_fail:
            GLib.timeout_add(self.wait_time, self.authentication_fail_cb)
        else:
            GLib.timeout_add(self.wait_time, self.connected_cb)

    def authentication_fail_cb(self):
        self.change_status(Garmin.Status.AUTHENTICATION_FAILED)

    def connected_cb(self):
        self.change_status(Garmin.Status.CONNECTED)
        GLib.timeout_add(self.wait_time, self.worker_cb)

    def worker_cb(self):
        while self.funcs:
            f, cb, args = self.funcs.pop(0)
            f(self, cb, *args)

        self.loop.quit()
        self.change_status(Garmin.Status.DISCONNECTED)

    @staticmethod
    def get_file_list(self, cb):
        base_path = os.environ.get('FAKE_GARMIN_BASE_PATH', None)
        if not base_path:
            base_path = os.path.join(GLib.get_user_config_dir(),
                'garmin-extractor', '3868484997')

        files = {}
        for filetype in FILETYPES:
            files[filetype] = []

        if 'FAKE_GARMIN_NO_ACTIVITIES' not in os.environ:
            path = os.path.join(base_path, 'activities')
            activities = os.listdir(path)

            random.shuffle(activities)

            for a in activities:
                files[ant.fs.file.File.Identifier.ACTIVITY].append(
                    FakeAntFile(base_path, a))

        GLib.idle_add(lambda: cb(files))

    def queue(self, func, cb, *args):
        self.funcs.append((func, cb, args))
        if self.status in [Garmin.Status.NONE, Garmin.Status.DISCONNECTED]:
            self.start()

    def shutdown(self):
        self.funcs = []
