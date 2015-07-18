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

from gi.repository import GObject

# TODO
GARMIN_NONE = 0
GARMIN_DISCONNECTED = 5

class queueable(object):
    def __init__(self, extra=None):
        self.extra = extra

    def __call__(self, f):
        def wrapper(*args):
            instance, cb = args[:2]
            instance.funcs.append((f, cb, args[2:]))

            if instance.status == GARMIN_NONE:
                instance.start()

            if self.extra:
                self.extra(instance)
        return wrapper

class GarminQueue(GObject.GObject):
    def __init__(self, cls):
        GObject.GObject.__init__(self)
        self.cls = cls
        self.garmin = None

    @GObject.Signal(arg_types=(object,))
    def garmin_changed(self, garmin):
        self.garmin = garmin

    def __getattr__(self, name):
        if name.startswith('_') or not hasattr(self.cls, name):
            return super(self).__getattr__(self, name)

        if not self.garmin:
            self.emit('garmin-changed', self.cls())
            self.garmin.connect('status-changed', self.status_changed_cb)

        def func(func_cb, *args):
            getattr(self.garmin, name)(func_cb, *args)
        return func

    def status_changed_cb(self, garmin, status):
        if status == GARMIN_DISCONNECTED:
            self.emit('garmin-changed', None)

    def shutdown(self):
        if self.garmin:
            self.garmin.shutdown()
