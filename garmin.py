import os
import sys
import array
import time

from gi.repository import GLib, GObject

import ant.fs.manager
import ant.fs.file

import utils

DIRECTORIES = {
    ".":            ant.fs.file.File.Identifier.DEVICE,
    "activities":   ant.fs.file.File.Identifier.ACTIVITY,
    "courses":      ant.fs.file.File.Identifier.COURSE,
    "monitoring_b": ant.fs.file.File.Identifier.MONITORING_B,
    #"profile":     ant.fs.file.File.Identifier.?
    #"goals?":      ant.fs.file.File.Identifier.GOALS,
    #"bloodprs":    ant.fs.file.File.Identifier.BLOOD_PRESSURE,
    #"summaries":   ant.fs.file.File.Identifier.ACTIVITY_SUMMARY,
    "settings":     ant.fs.file.File.Identifier.SETTING,
    "sports":       ant.fs.file.File.Identifier.SPORT,
    "totals":       ant.fs.file.File.Identifier.TOTALS,
    "weight":       ant.fs.file.File.Identifier.WEIGHT,
    "workouts":     ant.fs.file.File.Identifier.WORKOUT}

FILETYPES = dict((v, k) for (k, v) in DIRECTORIES.items())

class Device(object):

    class ProfileVersionMismatch(Exception):
        pass

    PROFILE_VERSION = 1
    PROFILE_VERSION_FILE = 'version'
    PASSKEY_FILE = 'authfile'
    NAME_FILE = 'name'

    def __init__(self, basedir, serial, name):
        self.path = os.path.join(basedir, str(serial))
        self.serial = serial
        self.name = name

        # check profile version, if not a new device
        if os.path.isdir(self.path):
            if self.version < self.PROFILE_VERSION:
                raise Device.ProfileVersionMismatch("Version on disk is too old")
            elif self.version > self.PROFILE_VERSION:
                raise Device.ProfileVersionMismatch("Version on disk is too new")

        # create directories
        utils.makedirs(self.path)
        for directory in DIRECTORIES:
            directory_path = os.path.join(self.path, directory)
            utils.makedirs(directory_path)

        # write profile version (if none)
        path = os.path.join(self.path, self.PROFILE_VERSION_FILE)
        if not os.path.exists(path):
            with open(path, 'wb') as f:
                f.write(str(self.PROFILE_VERSION))

        # write device name
        path = os.path.join(self.path, self.NAME_FILE)
        if not os.path.exists(path):
            with open(path, 'w') as f:
                f.write(self.name)

# TODO
#    @staticmethod
#    def from_saved(basedir, serial):
#        path = os.path.join(basedir, str(serial), self.NAME_FILE)
#
#        return Device(basedir, serial, name)

    @property
    def version(self):
        if not hasattr(self, '_version'):
            path = os.path.join(self.path, self.PROFILE_VERSION_FILE)

            if not os.path.exists(path):
                self._version = self.PROFILE_VERSION
            else:
                try:
                    with open(path, 'rb') as f:
                        self._version = int(f.read())
                except IOError as e:
                    self._version = 0

        return self._version

    @property
    def passkey(self):
        if not hasattr(self, '_passkey'):
            path = os.path.join(self.path, self.PASSKEY_FILE)
            try:
                with open(path, 'rb') as f:
                    self._passkey = array.array('B', f.read())
            except:
                self._passkey = None

        return self._passkey

    @passkey.setter
    def passkey(self, passkey):
        path = os.path.join(self.path, self.PASSKEY_FILE)
        with open(path, 'wb') as f:
            passkey.tofile(f)
        self._passkey = passkey

    @passkey.deleter
    def passkey(self):
        delattr(self, '_passkey')
        path = os.path.join(self.path, self.PASSKEY_FILE)
        try:
            os.unlink(path)
        except:
            pass

class AntFile(object):
    def __init__(self, device, antfile):
        self.antfile = antfile

        self.filename = '{0}_{1}_{2}.fit'.format(
            self.save_date.strftime("%Y-%m-%d_%H-%M-%S"), #, time.gmtime()), TODO
            self.antfile.get_fit_sub_type(),
            self.antfile.get_fit_file_number())

        self.path = os.path.join(device.path, FILETYPES[antfile.get_fit_sub_type()], self.filename)

    @property
    def save_date(self):
        return self.antfile.get_date()

    @property
    def index(self):
        return self.antfile.get_index()

class Garmin(ant.fs.manager.Application,
             GObject.GObject):

    PRODUCT_NAME = "correre"

    class Status:
        NONE = 0
        CONNECTING = 1
        AUTHENTICATION = 2
        AUTHENTICATION_FAILED = 3
        CONNECTED = 4
        DISCONNECTED = 5

    @GObject.Signal(arg_types=(int,))
    def status_changed(self, status):
        pass

    def __init__(self):
        ant.fs.manager.Application.__init__(self)
        GObject.GObject.__init__(self)

        self.path = os.path.join(GLib.get_user_config_dir(), self.PRODUCT_NAME)
        utils.makedirs(self.path)

        self.status = Garmin.Status.NONE
        self.device = None
        self.funcs = []

    def change_status(self, status):
        self.status = status
        # run in ui thread
        GLib.idle_add(lambda: self.emit('status-changed', status))

    def setup_channel(self, channel):
        channel.set_period(4096)
        channel.set_search_timeout(255)
        channel.set_rf_freq(50)
        channel.set_search_waveform([0x53, 0x00])
        channel.set_id(0, 0x01, 0)
        channel.open()

    def on_link(self, beacon):
        self.link()
        return True

    def on_authentication(self, beacon):
        self.change_status(Garmin.Status.AUTHENTICATION)
        serial, name = self.authentication_serial()
        device = Device(self.path, serial, name)

        passkey = device.passkey

        try:
            if device.passkey is not None:
                self.authentication_passkey(device.passkey)
            else:
                device.passkey = self.authentication_pair(self.PRODUCT_NAME)

            self.device = device
            return True
        except ant.fs.manager.AntFSAuthenticationException as e:
            self.change_status(Garmin.Status.AUTHENTICATION_FAILED)
            return False

    def on_transport(self, beacon):
        self.change_status(Garmin.Status.CONNECTED)

        while self.funcs:
            f, cb, args = self.funcs.pop(0)
            f(self, cb, *args)

    @staticmethod
    def get_file_list(self, cb):
        directory = self.download_directory()

        # get a list of remote files
        files = {}
        for filetype in FILETYPES:
            files[filetype] = []

        for antfile in directory.get_files():
            subtype = antfile.get_fit_sub_type()

            if subtype in files:
                files[subtype].append(AntFile(self.device, antfile))

        # run in ui thread
        GLib.idle_add(lambda: cb(files))

    @staticmethod
    def download_file(self, done_cb, antfile, progress_cb):
        def cb(new_progress):
            GLib.idle_add(lambda: progress_cb(new_progress))

        data = self.download(antfile.index, cb)

        # run in ui thread
        GLib.idle_add(lambda: done_cb(data))

    def queue(self, func, cb, *args):
        self.funcs.append((func, cb, args))
        if self.status in [Garmin.Status.NONE, Garmin.Status.DISCONNECTED]:
            self.start()

    def shutdown(self):
        self.funcs = []

    @utils.run_in_thread
    def start(self):
        if not self.funcs:
            return

        self.change_status(Garmin.Status.CONNECTING)
        ant.fs.manager.Application.start(self)

    def disconnect(self):
        ant.fs.manager.Application.disconnect(self)
        self.change_status(Garmin.Status.DISCONNECTED)
