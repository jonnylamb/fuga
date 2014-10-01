from gi.repository import Gtk

STATUSES = [ 'None',
             'Connecting',
             'Authentication',
             'Authentication Failed',
             'Connected',
             'Disconnected']

# TODO: everything

class LoadingWindow(Gtk.ApplicationWindow):

    def __init__(self, garmin):
        Gtk.ApplicationWindow.__init__(self)

        garmin.connect('status-changed', self.status_changed_cb)

        self.label = Gtk.Label()
        self.add(self.label)

    def status_changed_cb(self, garmin, status):
        self.label.set_text(STATUSES[status])
