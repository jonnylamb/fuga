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
import json
import sys

from gi.repository import GObject, Soup, GLib, Gio

import utils

ACTIVITY_URL = 'http://www.strava.com/activities/{}'
UPLOAD_URL = 'https://www.strava.com/api/v3/uploads'
UPLOAD_URL_WITH_ID = 'https://www.strava.com/api/v3/uploads/{}'
AUTH_URL = 'https://www.strava.com/oauth/authorize?client_id=362&response_type=code&redirect_uri=http://correre.jonnylamb.com&approval_prompt=force&scope=write'
CALLBACK_URL = 'http://correre.jonnylamb.com/'

class Uploader(GObject.GObject):

    class Status:
        NONE = 0
        UPLOADING = 1
        WAITING = 2
        DONE = 3
        ERROR = 4
        DUPLICATE = 5

    @GObject.Signal(arg_types=(int,))
    def status_changed(self, status):
        pass

    def __init__(self, activity):
        GObject.GObject.__init__(self)

        self.token = activity.app.config.get('strava', 'access_token')
        self.activity = activity

        self.session = Soup.Session()

        # somewhat public attrs
        self.id = None
        self.status = Uploader.Status.NONE
        self.error = None
        self.activity_id = None

    def change_status(self, status):
        if status == self.status:
            return
        self.status = status
        self.emit('status-changed', status)

    def start(self):
        f = Gio.File.new_for_path(self.activity.full_path)
        f.read_async(GLib.PRIORITY_DEFAULT, callback=self.read_cb)

    def read_cb(self, f, result):
        stream = f.read_finish(result)

        def cb(data):
            stream.close()
            self.file_loaded(data)
        utils.read_stream_async(stream, cb)

    def file_loaded(self, data):
        buff = Soup.Buffer.new(data)

        multipart = Soup.Multipart.new('multipart/form-data')
        multipart.append_form_string('data_type', 'fit')
        multipart.append_form_file('file', self.activity.filename, 'application/octet-stream', buff)

        message = Soup.form_request_new_from_multipart(UPLOAD_URL, multipart)
        message.request_headers.append('Authorization', 'Bearer {}'.format(self.token))

        self.session.send_async(message, callback=self.sent_cb)

        self.change_status(Uploader.Status.UPLOADING)

    def error_from_exception(self, e):
        self.error = e.message
        self.change_status(Uploader.Status.ERROR)

    def sent_cb(self, session, result):
        try:
            stream = session.send_finish(result)
        except Exception as e:
            self.error_from_exception(e)
            return

        def cb(data):
            stream.close()
            self.read_response(data)
        utils.read_stream_async(stream, cb)

    def read_response(self, raw):
        try:
            data = json.loads(raw)
        except Exception as e:
            self.error_from_exception(e)
            return

        self.id = data['id']

        if data['error']:
            self.error = data['error']

            if 'duplicate' in data['error']:
                self.activity_id = int(data['error'].split()[-1])
                self.change_status(Uploader.Status.DUPLICATE)
            else:
                self.change_status(Uploader.Status.ERROR)
            return

        if 'ready' in data['status']:
            self.activity_id = data['activity_id']
            self.change_status(Uploader.Status.DONE)
            return

        if 'still' in data['status']:
            self.change_status(Uploader.Status.WAITING)
            GLib.timeout_add_seconds(1, self.poll_status)

    def poll_status(self):
        message = Soup.Message.new('GET', UPLOAD_URL_WITH_ID.format(self.id))
        message.request_headers.append('Authorization', 'Bearer {}'.format(self.token))

        self.session.send_async(message, callback=self.sent_cb)
        return False

if __name__ == '__main__':
    token, path = sys.argv[1:]

    class FakeConfig(object):
        def __init__(self, token):
            self.token = token

        def get(self, key, item):
            if key == 'strava' and item == 'access_token':
                return self.token
            return None

    class FakeApp(object):
        def __init__(self, token):
            self.config = FakeConfig(token)

    class FakeActivity(object):
        def __init__(self, token, path):
            self.app = FakeApp(token)
            self.filename = os.path.basename(path)
            self.full_path = path

    activity = FakeActivity(token, path)

    uploader = Uploader(activity)
    loop = GObject.MainLoop()

    def status_changed_cb(uploader, status):
        if status == Uploader.Status.NONE:
            pass
        elif status == Uploader.Status.UPLOADING:
            print 'uploading...'
        elif status == Uploader.Status.WAITING:
            print 'waiting...'
        elif status == Uploader.Status.DONE:
            print 'done:', uploader.activity_id
            loop.quit()
        elif status == Uploader.Status.ERROR:
            print 'error:', uploader.error
            loop.quit()
        elif status == Uploader.Status.DUPLICATE:
            print 'duplicate:', uploader.activity_id
            loop.quit()
    uploader.connect('status-changed', status_changed_cb)

    uploader.start()
    loop.run()
