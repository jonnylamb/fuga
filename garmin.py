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
import sys
import array
import time
from datetime import datetime

from gi.repository import GLib, GObject

import ant.fs.manager
import ant.fs.file
from ant.fs.command import EraseRequestCommand, EraseResponse

from queue import queueable
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
            self.save_date.strftime("%Y-%m-%d_%H-%M-%S"),
            self.antfile.get_fit_sub_type(),
            self.antfile.get_fit_file_number())

        self.path = os.path.join(device.path, FILETYPES[antfile.get_fit_sub_type()], self.filename)

    @property
    def save_date(self):
        dt = self.antfile.get_date()

        # we have to do this silly conversion to get the utc datetime.
        # openant already creates a datetime for us, but it's in the
        # local tz.
        seconds = (dt - datetime.fromtimestamp(0)).total_seconds()

        return datetime.utcfromtimestamp(seconds)

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

        self.loop = None
        self.timeout_source = None

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

        while True:
            if self.timeout_source:
                self.timeout_source = None
                return

            while self.funcs:
                f, cb, args = self.funcs.pop(0)
                ret = f(self, *args)
                # run in ui thread
                GLib.idle_add(lambda: cb(ret))

            # we've run out of things to do for now. set a timer so we don't
            # disconnect immediately.

            # use a new context as we don't want to get mixed up with the
            # other mainloop currently running
            context = GLib.MainContext()
            self.loop = GLib.MainLoop(context)
            def timeout_cb(data=None):
                self.loop.quit()
                self.loop = None
            self.timeout_source = GLib.timeout_source_new_seconds(5)
            self.timeout_source.set_callback(timeout_cb)
            self.timeout_source.attach(context)
            self.loop.run()

    def cancel_timer(self, remove_source=False):
        if self.timeout_source:
            self.timeout_source.destroy()
            if remove_source:
                self.timeout_source = None
            self.loop.quit()
            self.loop = None

    @queueable(lambda self: self.cancel_timer(True))
    def get_file_list(self):
        directory = self.download_directory()

        # get a list of remote files
        files = {}
        for filetype in FILETYPES:
            files[filetype] = []

        for antfile in directory.get_files():
            subtype = antfile.get_fit_sub_type()

            if subtype in files:
                files[subtype].append(AntFile(self.device, antfile))

        return files

    @queueable(lambda self: self.cancel_timer(True))
    def download_file(self, antfile, progress_cb):
        def cb(new_progress):
            GLib.idle_add(lambda: progress_cb(new_progress))

        return self.download(antfile.index, cb)

    @queueable(lambda self: self.cancel_timer(True))
    def delete_file(self, antfile):
        return self.erase(antfile.index)

    def shutdown(self):
        self.funcs = []
        self.cancel_timer()

    @utils.run_in_thread
    def start(self):
        if not self.funcs:
            return

        self.change_status(Garmin.Status.CONNECTING)
        ant.fs.manager.Application.start(self)

    def disconnect(self):
        ant.fs.manager.Application.disconnect(self)
        self.change_status(Garmin.Status.DISCONNECTED)

    # https://github.com/Tigge/openant/pull/3
    def erase(self, index):
        self._send_command(EraseRequestCommand(index))
        response = self._get_command()
        arg = response._get_argument("response")

        if arg == EraseResponse.Response.ERASE_SUCCESSFUL:
            return True
        else:
            return False
