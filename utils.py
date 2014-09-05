import os
import errno

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