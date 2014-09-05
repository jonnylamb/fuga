import os
import pickle
import random
from datetime import datetime

from gi.repository import GLib, GObject

import ant.fs.file

from garmin import Garmin, FILETYPES, AntFile

ACTIVITIES = ['2014-04-01_21-16-44_4_75',
              '2014-04-03_15-56-20_4_76',
              '2014-04-04_19-02-40_4_77',
              '2014-04-05_12-20-56_4_78',
              '2014-04-09_22-11-08_4_79',
              '2014-04-12_23-37-02_4_80',
              '2014-04-13_00-58-18_4_81',
              '2014-04-14_17-14-02_4_82',
              '2014-04-15_22-20-50_4_83',
              '2014-04-16_19-52-22_4_84',
              '2014-04-22_21-11-52_4_87',
              '2014-05-05_20-31-56_4_94',
              '2014-05-23_20-59-26_4_98',
              '2014-05-26_19-19-22_4_99',
              '2014-05-30_13-58-02_4_101',
              '2014-05-30_16-18-58_4_102',
              '2014-06-03_16-14-16_4_103',
              '2014-06-04_23-25-56_4_104',
              '2014-06-07_08-36-00_4_105',
              '2014-06-08_08-20-18_4_106',
              '2014-06-11_21-52-02_4_109',
              '2014-06-20_14-57-36_4_111',
              '2014-06-22_19-22-12_4_112',
              '2014-06-23_12-35-56_4_113',
              '2014-06-27_17-36-16_4_114',
              '2014-06-28_08-57-20_4_115',
              '2014-06-28_09-45-46_4_116',
              '2014-06-28_13-01-34_4_117',
              '2014-07-15_10-20-36_4_118',
              '2014-07-16_17-18-38_4_119',
              '2014-07-16_17-49-42_4_120',
              '2014-07-25_10-30-50_4_121',
              '2014-08-05_00-40-54_4_123',
              '2014-08-06_23-20-40_4_125',
              '2014-08-08_20-35-54_4_126',
              '2014-08-13_22-42-36_4_128',
              '2014-08-17_10-22-22_4_129',
              '2014-08-19_00-22-42_4_130',
              '2014-08-20_22-39-48_4_131']




class FakeAntFile(object):
    def __init__(self, name):
        self.filename = name + '.fit'

        date, time, subtype, number = name.split('_')
        self.date = datetime.strptime(date + '_' + time, '%Y-%m-%d_%H-%M-%S')

        # todo
        self.path = os.path.join(GLib.get_user_config_dir(),
            'garmin-extractor', '3868484997', FILETYPES[int(subtype)], self.filename)

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

        # shuffle the activities list as we don't depend on an ordering.
        # doing it in place is a bit horrible
        random.shuffle(ACTIVITIES)

        if 'FAKE_GARMIN_NO_ACTIVITIES' not in os.environ:
            for a in ACTIVITIES:
                files[ant.fs.file.File.Identifier.ACTIVITY].append(FakeAntFile(a))

        self.emit('files', pickle.dumps(files)) # TODO

        self.stop()

    def stop(self):
        self.emit('status-changed', Garmin.Status.DISCONNECTED)
        self.loop.quit()
