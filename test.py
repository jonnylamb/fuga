import os
import pickle

from garmin import Garmin
from fakegarmin import FakeGarmin
import ant.fs.file

if os.getenv('FAKE_GARMIN'):
    g = FakeGarmin()
else:
    g = Garmin()

statuses = {
    Garmin.Status.NONE: 'none',
    Garmin.Status.CONNECTING: 'connecting',
    Garmin.Status.AUTHENTICATION: 'authentication',
    Garmin.Status.AUTHENTICATION_FAILED: 'authentication failed',
    Garmin.Status.CONNECTED: 'connected'
    }

def status_changed_cb(g, status):
    print 'status changed: {}'.format(statuses[status])
g.connect('status-changed', status_changed_cb)

def files_cb(g, p):
    files = pickle.loads(p) # TODO

    activities = files[ant.fs.file.File.Identifier.ACTIVITY]

    for activity in activities:
        print activity.date
        print ' - filename:', activity.path
        print ' - exists:', activity.exists

g.connect('files', files_cb)

g.start()
g.stop()

