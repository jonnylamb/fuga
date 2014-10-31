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
