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

    __gsignals__ = {
        'parsed': (GObject.SIGNAL_RUN_FIRST, None,
            ())
    }

    def __init__(self, filename):
        GObject.GObject.__init__(self)

        self.filename = filename

        self.fit = fitparse.FitFile(filename,
            data_processor=fitparse.StandardUnitsDataProcessor())
        self.summary = None

        self.parsed = False
        self.parsing = False

    @run_in_thread
    def parse(self):
        if self.parsing:
            return
        self.parsing = True

        self.fit.parse()

        # is this always right? no idea.
        msg = self.fit.messages[-2]
        if msg.type is 'data' and msg.name is 'session':
            self.summary = msg

        def emit_parsed():
            self.parsed = True
            self.parsing = False
            self.emit('parsed')
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