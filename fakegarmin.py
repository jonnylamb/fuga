import os
import pickle
import random
from datetime import datetime

from gi.repository import GLib, GObject

import ant.fs.file

from garmin import Garmin, FILETYPES, AntFile

class FakeAntFile(object):
    def __init__(self, base_path, name):
        self.filename = name

        date, time, subtype, number = name.split('_')
        self.date = datetime.strptime(date + '_' + time, '%Y-%m-%d_%H-%M-%S')

        self.path = os.path.join(base_path, FILETYPES[int(subtype)], self.filename)

class FakeGarmin(GObject.GObject):

    @GObject.Signal(arg_types=(int,))
    def status_changed(self, status):
        pass

    @GObject.Signal(arg_types=(str,))
    def files(self, files):
        pass

    def __init__(self, authentication_fail=False):
        GObject.GObject.__init__(self)

        self.loop = GObject.MainLoop()

        self.authentication_fail = authentication_fail

        self.wait_time = int(os.environ.get('FAKE_GARMIN_TIME', 200))

        # todo
        self.base_path = os.path.join(GLib.get_user_config_dir(),
            'garmin-extractor', '3868484997')

    def start(self):
        self.emit('status-changed', Garmin.Status.CONNECTING)

        GLib.timeout_add(self.wait_time, self.authentication_cb)
        self.loop.run()

    def authentication_cb(self):
        self.emit('status-changed', Garmin.Status.AUTHENTICATION)

        if self.authentication_fail:
            GLib.timeout_add(self.wait_time, self.authentication_fail_cb)
        else:
            GLib.timeout_add(self.wait_time, self.connected_cb)

    def authentication_fail_cb(self):
        self.emit('status-changed', Garmin.Status.AUTHENTICATION_FAILED)

    def connected_cb(self):
        self.emit('status-changed', Garmin.Status.CONNECTED)

        GLib.timeout_add(self.wait_time, self.files_cb)

    def files_cb(self):
        files = {}
        for filetype in FILETYPES:
            files[filetype] = []

        if 'FAKE_GARMIN_NO_ACTIVITIES' not in os.environ:
            path = os.path.join(self.base_path, 'activities')
            activities = os.listdir(path)

            # shuffle the activities list as we don't depend on an ordering.
            random.shuffle(activities)

            for a in activities:
                files[ant.fs.file.File.Identifier.ACTIVITY].append(
                    FakeAntFile(self.base_path, a))

        self.emit('files', pickle.dumps(files)) # TODO

        self.stop()

    def stop(self):
        self.emit('status-changed', Garmin.Status.DISCONNECTED)
        self.loop.quit()
