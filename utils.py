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
import errno
import threading

from gi.repository import GLib

def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

BYTES = 4096

def read_stream_cb(stream, result, user_data):
    cb, data = user_data
    bytes = stream.read_bytes_finish(result)

    data += bytes.get_data()

    if bytes.get_size() < BYTES:
        cb(data)
        return

    read_stream_async(stream, cb, data)

def read_stream_async(stream, cb, data=''):
    stream.read_bytes_async(BYTES, GLib.PRIORITY_DEFAULT,
        callback=read_stream_cb, user_data=(cb, data))

# http://amix.dk/blog/post/19346
def run_in_thread(fn):
    def run(*k, **kw):
        t = threading.Thread(target=fn, args=k, kwargs=kw)
        t.start()
    return run
