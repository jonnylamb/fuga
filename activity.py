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
from datetime import datetime

from gi.repository import GObject, Gio, Gtk

import fit
import strava

class Activity(GObject.GObject):

    class Status:
        NONE = 0 # only on the device
        DOWNLOADING = 1
        DOWNLOADED = 2
        PARSING = 3
        PARSED = 4
        DELETED = 5

    def __init__(self, app, antfile):
        GObject.GObject.__init__(self)

        self.app = app
        self.antfile = antfile
        self.fit = None
        self.status = Activity.Status.NONE
        self.uploader = None

        self.setup_fit()

    def setup_fit(self):
        if self.downloaded:
            self.fit = fit.Fit(self.full_path)
            self.fit.connect('status-changed', self.fit_status_changed_cb)
            self.status = Activity.Status.DOWNLOADED

    def fit_status_changed_cb(self, f, status):
        mapping = {
            fit.Fit.Status.PARSING: Activity.Status.PARSING,
            fit.Fit.Status.PARSED: Activity.Status.PARSED,
        }

        for fstatus, astatus in mapping.items():
            if status == fstatus:
                self.change_status(astatus)

        # cache a bit of information
        if status == fit.Fit.Status.PARSED:
            if self.fit.get_sport():
                # string
                self.set_config('sport', self.fit.get_sport())
                # float
                self.set_config('distance', self.fit.get_distance())
                # float
                self.set_config('elapsed_time',
                    self.fit.get_elapsed_time(triplet=False))
                # string
                start_time = self.fit.get_start_time()
                self.set_config('start_time',
                    start_time.strftime('%Y-%m-%d %H:%M:%S'))

    # signals: because GObject doesn't support multiple inheritance, every
    # signal here will have to be copied into any subclass manually
    @GObject.Signal(arg_types=(int,))
    def status_changed(self, status):
        pass

    @GObject.Signal(arg_types=(int,))
    def strava_id_updated(self, status):
        # have a different signal for this and not just another Activity
        # status because we don't want to redraw the entire map widget just to
        # change the text on one button.
        pass

    @GObject.Signal(arg_types=(float,))
    def download_progress(self, fraction):
        pass

    # config options
    def get_config(self, key, default=None):
        if self.app.config.has_option(self.filename, key):
            return self.app.config.get(self.filename, key)
        return default

    def set_config(self, key, value):
        if not self.app.config.has_section(self.filename):
            self.app.config.add_section(self.filename)
        self.app.config.set(self.filename, key, value)
        self.app.config.save()

    # properties
    @property
    def filename(self):
        return self.antfile.filename

    @property
    def full_path(self):
        return self.antfile.path

    @property
    def uri(self):
        gfile = Gio.File.new_for_path(self.full_path)
        return gfile.get_uri()

    @property
    def downloaded(self):
        return os.path.exists(self.full_path)

    @property
    def strava_id(self):
        ret = self.get_config('strava_id')
        return ret if ret is None else int(ret)

    @strava_id.setter
    def strava_id(self, new_id):
        self.set_config('strava_id', str(new_id))
        self.emit('strava-id-updated', new_id)

    @property
    def date(self):
        if self.status == Activity.Status.PARSED:
            return self.fit.get_start_time()
        else:
            start = self.get_config('start_time')
            if start:
                return datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
            return self.antfile.save_date

    @property
    def sport(self):
        if self.status == Activity.Status.PARSED:
            return self.fit.get_sport()

        # will default to None
        return self.get_config('sport')

    # helper funcs
    def change_status(self, status):
        self.status = status
        self.emit('status-changed', status)

    @staticmethod
    def sort_func(activity1, activity2, unused=None):
        # use the antfile save date otherwise order can change depending on
        # what has been ordered
        if activity1.antfile.save_date > activity2.antfile.save_date:
            return -1
        elif activity1.antfile.save_date < activity2.antfile.save_date:
            return 1
        else:
            return 0

    def parse(self):
        # deliberately break if self.fit is None
        self.fit.parse()

    def upload(self):
        if self.uploader:
            return self.uploader

        self.uploader = strava.Uploader(self)

        def status_changed_cb(uploader, status):
            if status in (strava.Uploader.Status.DONE,
                    strava.Uploader.Status.DUPLICATE):
                self.strava_id = uploader.activity_id

            if status in (strava.Uploader.Status.DONE,
                    strava.Uploader.Status.ERROR,
                    strava.Uploader.Status.DUPLICATE):
                self.uploader = None

        self.uploader.connect('status-changed', status_changed_cb)

        return self.uploader

    def download(self):
        if self.downloaded:
            return

        if self.status == Activity.Status.DOWNLOADING:
            return

        def progress_cb(fraction):
            self.emit('download-progress', fraction)

        self.app.queue.download_file(self.file_downloaded_cb,
            self.antfile, progress_cb)

        self.change_status(Activity.Status.DOWNLOADING)

    def file_downloaded_cb(self, data):
        with open(self.full_path, 'wb') as f:
            f.write(data)
        self.setup_fit()
        self.change_status(Activity.Status.DOWNLOADED)

        recent = Gtk.RecentManager()
        recent.add_item(self.uri)

    def delete(self):
        self.app.queue.delete_file(self.delete_cb, self.antfile)

    def delete_cb(self, result):
        if result:
            self.change_status(Activity.Status.DELETED)
        else:
            # delete failed
            self.change_status(Activity.Status.PARSED)
