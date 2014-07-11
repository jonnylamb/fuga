import os
import pickle
import random
from datetime import datetime

from gi.repository import GLib, GObject

import ant.fs.file

from garmin import Garmin, FILETYPES, AntFile

ACTIVITIES = ['2013-11-27_20-45-22_4_1',
              '2013-11-27_21-45-22_4_1',
              '2013-12-02_22-50-40_4_2',
              '2013-12-02_23-50-40_4_2',
              '2013-12-04_22-53-38_4_3',
              '2013-12-04_23-53-38_4_3',
              '2013-12-06_18-44-34_4_4',
              '2013-12-06_19-44-34_4_4',
              '2013-12-09_22-30-10_4_5',
              '2013-12-09_23-30-10_4_5',
              '2013-12-11_21-31-46_4_6',
              '2013-12-11_22-31-46_4_6',
              '2013-12-22_12-20-30_4_7',
              '2013-12-22_13-20-30_4_7',
              '2013-12-24_15-49-44_4_8',
              '2013-12-24_16-49-44_4_8',
              '2013-12-27_12-13-40_4_9',
              '2013-12-27_13-13-40_4_9',
              '2014-01-02_10-33-56_4_10',
              '2014-01-02_11-33-56_4_10',
              '2014-01-04_12-08-40_4_11',
              '2014-01-04_13-08-40_4_11',
              '2014-01-10_13-23-28_4_12',
              '2014-01-10_14-23-28_4_12',
              '2014-01-12_11-28-16_4_13',
              '2014-01-12_12-28-16_4_13',
              '2014-01-13_21-28-02_4_14',
              '2014-01-13_21-52-40_4_15',
              '2014-01-16_09-31-40_4_16',
              '2014-01-16_10-46-22_4_17',
              '2014-01-17_10-56-26_4_18',
              '2014-01-17_18-47-38_4_19',
              '2014-01-18_23-51-44_4_20',
              '2014-01-20_13-37-42_4_21',
              '2014-01-20_13-37-44_4_22',
              '2014-01-20_13-37-46_4_23',
              '2014-01-20_13-37-48_4_24',
              '2014-01-20_13-37-50_4_25',
              '2014-01-20_13-37-52_4_26',
              '2014-01-20_13-37-52_4_27',
              '2014-01-21_10-47-20_4_28',
              '2014-01-23_21-02-22_4_29',
              '2014-01-25_11-39-50_4_30',
              '2014-01-25_16-35-26_4_31',
              '2014-01-27_11-49-02_4_32',
              '2014-01-29_10-02-24_4_33',
              '2014-01-30_22-34-32_4_34',
              '2014-02-02_22-18-36_4_35',
              '2014-02-03_16-24-16_4_36',
              '2014-02-04_16-14-48_4_37',
              '2014-02-05_13-59-28_4_38',
              '2014-02-05_17-08-52_4_39',
              '2014-02-06_15-50-08_4_40',
              '2014-02-07_18-19-46_4_41']

class FakeAntFile(object):
    def __init__(self, name):
        self.filename = name + '.fit'

        date, time, subtype, number = name.split('_')
        self.date = datetime.strptime(date + '_' + time, '%Y-%m-%d_%H-%M-%S')

        # todo
        self.path = os.path.join('/tmp', FILETYPES[int(subtype)], self.filename)
        self.exists = bool(random.randint(0, 1))

class FakeGarmin(GObject.GObject):

    __gsignals__ = {
        'status-changed': (GObject.SIGNAL_RUN_FIRST, None,
            (int,)),
        'files': (GObject.SIGNAL_RUN_FIRST, None,
            (str,)) # TODO
    }

    def __init__(self, authentication_fail=False):
        GObject.GObject.__init__(self)

        self.loop = GObject.MainLoop()

        self.authentication_fail = authentication_fail

        self.wait_time = int(os.getenv('FAKE_GARMIN_TIME', 1))

    def start(self):
        self.emit('status-changed', Garmin.Status.CONNECTING)

        GLib.timeout_add_seconds(self.wait_time, self.authentication_cb)
        self.loop.run()

    def authentication_cb(self):
        self.emit('status-changed', Garmin.Status.AUTHENTICATION)

        if self.authentication_fail:
            GLib.timeout_add_seconds(self.wait_time, self.authentication_fail_cb)
        else:
            GLib.timeout_add_seconds(self.wait_time, self.connected_cb)

    def authentication_fail_cb(self):
        self.emit('status-changed', Garmin.Status.AUTHENTICATION_FAILED)

    def connected_cb(self):
        self.emit('status-changed', Garmin.Status.CONNECTED)

        GLib.timeout_add_seconds(self.wait_time, self.files_cb)

    def files_cb(self):
        files = {}
        for filetype in FILETYPES:
            files[filetype] = []

        # shuffle the activities list s we don't depend on an ordering
        # doing it in place is a bit horrible
        random.shuffle(ACTIVITIES)

        if not os.getenv('FAKE_GARMIN_NO_ACTIVITIES'):
            for a in ACTIVITIES:
                files[ant.fs.file.File.Identifier.ACTIVITY].append(FakeAntFile(a))

        self.emit('files', pickle.dumps(files)) # TODO

        self.stop()

    def stop(self):
        self.emit('status-changed', Garmin.Status.DISCONNECTED)
        self.loop.quit()
