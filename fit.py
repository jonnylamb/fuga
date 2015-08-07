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

import fitparse
from fitparse.base import FitParseError

from gi.repository import GObject

from utils import run_in_thread

class Fit(GObject.GObject):

    class Status:
        NONE = 0
        PARSING = 1
        PARSED = 2
        FAILED = 3

    @GObject.Signal(arg_types=(int,))
    def status_changed(self, status):
        pass

    def __init__(self, filename):
        GObject.GObject.__init__(self)

        self.filename = filename

        self.summary = None

        self.status = Fit.Status.NONE

    @run_in_thread
    def parse(self):
        if self.status != Fit.Status.NONE:
            return
        self.status = Fit.Status.PARSING
        self.emit('status-changed', self.status)

        try:
            self.fit = fitparse.FitFile(self.filename,
                data_processor=fitparse.StandardUnitsDataProcessor())
        except FitParseError:
            self.status = Fit.Status.FAILED
            GObject.idle_add(lambda: self.emit('status-changed', self.status))
            return

        self.fit.parse()

        # find the summary message
        for msg in self.fit.messages:
            if msg.name == 'session':
                self.summary = msg
                break

        self.status = Fit.Status.PARSED
        GObject.idle_add(lambda: self.emit('status-changed', self.status))

    def records(self):
        for m in self.fit.messages:
            if m.name == 'record':
                yield m

    def get(self, name, default=0):
        if not self.summary:
            return default

        val = self.summary.get(name)
        if not val or val.value is None:
            return default

        return val.value

    def time_triplet(self, seconds):
        seconds = int(seconds)
        return (seconds // 3600,
            (seconds % 3600) // 60,
            seconds % 60)

    # convenience methods
    def get_sport(self):
        return self.get('sport', '')

    def get_distance(self):
        return self.get('total_distance')

    def get_elevation(self):
        return self.get('total_ascent')

    def get_elapsed_time(self, triplet=True):
        if triplet:
            return self.time_triplet(self.get('total_elapsed_time'))
        else:
            return self.get('total_elapsed_time')

    def get_moving_time(self):
        return self.time_triplet(self.get('total_timer_time'))

    def get_start_time(self):
        return self.get('start_time')
