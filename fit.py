import threading

import fitparse

from gi.repository import GObject

# http://amix.dk/blog/post/19346
def run_in_thread(fn):
    def run(*k, **kw):
        t = threading.Thread(target=fn, args=k, kwargs=kw)
        t.start()
    return run

class Fit(GObject.GObject):

    class Status:
        NONE = 0
        PARSING = 1
        PARSED = 2

    @GObject.Signal(arg_types=(int,))
    def status_changed(self, status):
        pass

    def __init__(self, filename):
        GObject.GObject.__init__(self)

        self.filename = filename

        self.fit = fitparse.FitFile(filename,
            data_processor=fitparse.StandardUnitsDataProcessor())
        self.summary = None

        self.status = Fit.Status.NONE

    @run_in_thread
    def parse(self):
        if self.status != Fit.Status.NONE:
            return
        self.status = Fit.Status.PARSING
        self.emit('status-changed', self.status)

        self.fit.parse()

        # is this always right? no idea.
        msg = self.fit.messages[-2]
        if msg.type == 'data' and msg.name == 'session':
            self.summary = msg

        def emit_parsed():
            self.status = Fit.Status.PARSED
            self.emit('status-changed', self.status)
        GObject.idle_add(emit_parsed)

    def records(self):
        for m in self.fit.messages:
            if m.name == 'record':
                yield m

    def get(self, name, default=0):
        if not self.summary:
            return default

        val = self.summary.get(name)
        if not val:
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

    def get_elapsed_time(self):
        return self.time_triplet(self.get('total_elapsed_time'))

    def get_moving_time(self):
        return self.time_triplet(self.get('total_timer_time'))

    def get_start_time(self):
        return self.get('start_time')
