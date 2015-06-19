from gi.repository import Gtk

STATUSES = [ 'None',
             'Connecting',
             'Authentication',
             'Authentication Failed',
             'Connected',
             'Disconnected']

class LoadingHeader(Gtk.HeaderBar):
    def __init__(self):
        Gtk.HeaderBar.__init__(self)

        self.set_title('Loading')

        self.next_button = Gtk.Button('Next')
        self.next_button.set_sensitive(False)
        self.next_button.get_style_context().add_class('suggested-action')
        self.pack_end(self.next_button)

class Loading(Gtk.Bin):
    def __init__(self, app):
        Gtk.Bin.__init__(self)

        self.app = app

        def changed_cb(queue, garmin):
            if not garmin:
                return
            garmin.connect('status-changed', self.status_changed_cb)
        app.queue.connect('garmin-changed', changed_cb)

        self.label = Gtk.Label()
        self.add(self.label)

    def status_changed_cb(self, garmin, status):
        self.label.set_text(STATUSES[status])

    def show_all(self):
        Gtk.Bin.show_all(self)
        self.app.mark_busy()

    def hide(self):
        Gtk.Bin.hide(self)
        self.app.unmark_busy()
