from gi.repository import Gtk

STATUSES = [ 'None',
             'Connecting',
             'Authentication',
             'Authentication Failed',
             'Connected',
             'Disconnected']

# TODO: everything

class LoadingWindow(Gtk.ApplicationWindow):

    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self)

        def changed_cb(queue, garmin):
            if not garmin:
                return
            garmin.connect('status-changed', self.status_changed_cb)
        app.queue.connect('garmin-changed', changed_cb)

        self.label = Gtk.Label()
        self.add(self.label)

    def status_changed_cb(self, garmin, status):
        self.label.set_text(STATUSES[status])
