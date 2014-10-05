import os
import random
from threading import Thread
import json
from datetime import datetime

from gi.repository import GtkClutter, Clutter
GtkClutter.init([])
from gi.repository import Gtk, GLib, GObject, Gio, Pango, Gdk, GtkChamplain, Champlain, WebKit

import fitparse

import fit
import strava

class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self)

        self.app = app

        self.activities = []

        self.set_default_size(1000, 700)
        self.set_title('Correre')

        #  titlebar
        titlebar_box = Gtk.Box()
        self.set_titlebar(titlebar_box)

        # left toolbar
        self.left_toolbar = Gtk.HeaderBar()
        self.left_toolbar.set_title('All activities')
        self.left_toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_TITLEBAR)
        self.left_toolbar.get_style_context().add_class('contacts-left-header-bar')
        titlebar_box.pack_start(self.left_toolbar, False, False, 0)

        # select button
        self.select_button = Gtk.ToggleButton()
        self.select_button.set_focus_on_click(False)
        self.select_button.set_sensitive(False)
        image = Gtk.Image(icon_name='object-select-symbolic', icon_size=Gtk.IconSize.MENU)
        self.select_button.set_image(image)
        self.left_toolbar.pack_end(self.select_button)

        self.select_button.connect('toggled', self.select_toggled_cb)
        self.num_selected = 0

        # right toolbar
        self.right_toolbar = Gtk.HeaderBar()
        self.right_toolbar.set_show_close_button(True)
        self.right_toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_TITLEBAR)
        self.right_toolbar.get_style_context().add_class('contacts-right-header-bar')
        titlebar_box.pack_start(self.right_toolbar, True, True, 0)

        # delete button
        self.delete_button = Gtk.Button(label='Delete')
        self.delete_button.get_style_context().add_class('destructive-action')
        self.delete_button.set_no_show_all(True)
        self.right_toolbar.pack_end(self.delete_button)

        # keep all menu buttons the same height
        vsize_group = Gtk.SizeGroup(Gtk.SizeGroupMode.VERTICAL)
        vsize_group.add_widget(self.select_button)
        vsize_group.add_widget(self.delete_button)

        # content box
        self.hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL, 0)
        self.add(self.hbox)

        # activity list pane
        self.pane = ListPane()
        self.hbox.pack_start(self.pane, False, False, 0)
        self.pane.set_size_request(300, -1)

        self.pane.activity_list.connect('row-selected', self.row_selected_cb)

        # keep left pane and toolbar the same width
        hsize_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        hsize_group.add_widget(self.left_toolbar)
        hsize_group.add_widget(self.pane)

        self.content = NoActivities()
        self.hbox.pack_start(self.content, True, True, 0)

    def add_activity(self, antfile):
        row = ActivityRow(self, self.app, antfile)
        row.selector_button.connect('toggled', self.activity_toggled_cb)
        self.pane.activity_list.prepend(row)
        self.activities.append(row)

        self.activities.sort(Activity.sort_func)

        # not at all necessary to enable unless the listview row starts
        # showing actual details about the activity
        #self.parse_all()

        self.select_button.set_sensitive(True)

    def parse_all(self, unused=None):
        def idle():
            for activity in self.activities:
                if not activity.downloaded:
                    continue

                if activity.status == Activity.Status.DOWNLOADED:
                    activity.connect('status-changed', self.parse_all)
                    activity.parse()
                    return

        GLib.idle_add(idle)

    def activity_toggled_cb(self, selector):
        if selector.get_active():
            self.num_selected += 1
        else:
            self.num_selected -= 1

        if self.num_selected > 0:
            self.left_toolbar.set_title('{} selected'.format(self.num_selected))
            self.pane.delete_button.set_sensitive(True)
        else:
            self.left_toolbar.set_title('Select')
            self.pane.delete_button.set_sensitive(False)

    def select_toggled_cb(self, toggle_button):
        if toggle_button.get_active():
            self.left_toolbar.get_style_context().add_class('selection-mode')
            self.right_toolbar.get_style_context().add_class('selection-mode')

            for activity in self.activities:
                activity.selector_button.show()
                activity.selector_button.set_hexpand(not activity.spinner.get_visible())

            self.left_toolbar.set_title('Select')

            self.delete_button.hide()
            self.pane.revealer.set_reveal_child(True)

            self.right_toolbar.set_show_close_button(False)

        else:
            self.left_toolbar.get_style_context().remove_class('selection-mode')
            self.right_toolbar.get_style_context().remove_class('selection-mode')

            for activity in self.activities:
                activity.selector_button.hide()
                activity.selector_button.set_active(False)

            self.num_selected = 0

            self.left_toolbar.set_title('All activities')

            activity = self.pane.activity_list.get_selected_row()
            self.delete_button.set_visible(
                activity.status == Activity.Status.PARSED)

            self.pane.revealer.set_reveal_child(False)

            self.right_toolbar.set_show_close_button(True)

    def row_selected_cb(self, activity_list, activity):
        if not activity:
            return

        self.reset_content(activity)

    def activity_status_changed_cb(self, activity, status):
        self.reset_content(activity)

    def reset_content(self, activity):
        if self.content:
            self.content.destroy()
            self.content = None

        # on device but not computer
        if activity.status == Activity.Status.NONE:
            self.content = ActivityMissingDetails(activity)

        # currently downloading
        elif activity.status == Activity.Status.DOWNLOADING:
            self.content = ActivityDownloadingDetails(activity)

        # finished downloading
        elif activity.status == Activity.Status.DOWNLOADED:
            activity.parse()
            self.content = Gtk.Spinner()
            self.content.start()

        # currently parsing
        elif activity.status == Activity.Status.PARSING:
            self.content = Gtk.Spinner()
            self.content.start()

        # finished parsing
        elif activity.status == Activity.Status.PARSED:
            self.content = ActivityDetails(activity)

        self.delete_button.set_visible(
            activity.status == Activity.Status.PARSED and \
            not self.select_button.get_active())

        self.hbox.pack_start(self.content, True, True, 0)
        self.content.show_all()

        title = activity.date.strftime('%A %d %B at %H:%M')
        self.right_toolbar.set_title(title)

        # once the focused activity is changed we want to stop listening to
        # its status-changed signal. in most cases this isn't a problem but if
        # you select an activity, press download, and change activity, once
        # the first activity is downloaded the content will change.
        def content_destroy_cb(widget, activity):
            try:
                activity.disconnect_by_func(self.activity_status_changed_cb)
            except TypeError:
                pass
        self.content.connect('destroy', content_destroy_cb, activity)

        activity.connect('status-changed', self.activity_status_changed_cb)

class ListPane(Gtk.Frame):
    def __init__(self):
        Gtk.Frame.__init__(self)

        self.set_hexpand(False)

        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.add(grid)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER,
                            Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_shadow_type(Gtk.ShadowType.NONE)
        grid.add(scrolled)

        self.activity_list = ActivityList()
        scrolled.add(self.activity_list)

        # revealer
        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        grid.add(self.revealer)

        bar = Gtk.ActionBar()
        self.revealer.add(bar)

        # TODO: add upload button
        self.delete_button = Gtk.Button('Delete')
        self.delete_button.get_style_context().add_class('destructive-action')
        self.delete_button.set_sensitive(False)
        bar.pack_end(self.delete_button)

class ActivityList(Gtk.ListBox):
    def __init__(self):
        Gtk.ListBox.__init__(self)

        self.set_selection_mode(Gtk.SelectionMode.BROWSE)
        self.set_header_func(self.update_header, None)
        self.set_sort_func(Activity.sort_func, None)

        color = Gdk.RGBA()
        color.parse('#ebebed')
        self.override_background_color(0, color)

        label = Gtk.Label('No activities')
        self.set_placeholder(label)
        label.show()

    def update_header(self, row, before_row, unused):
        current = row.get_header()

        if before_row and (not current or not isinstance(current, Gtk.Separator)):
            row.set_header(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        else:
            row.set_header(None)

class Activity(GObject.GObject):

    class Status:
        NONE = 0 # only on the device
        DOWNLOADING = 1
        DOWNLOADED = 2
        PARSING = 3
        PARSED = 4

    def __init__(self, app, antfile):
        GObject.GObject.__init__(self)

        self.app = app
        self.antfile = antfile
        self.fit = None
        self.status = Activity.Status.NONE
        self.uploader = None

        if self.downloaded:
            self.fit = fit.Fit(self.full_path)
            self.fit.connect('status-changed', self.fit_status_changed_cb)
            self.status = Activity.Status.DOWNLOADED

    def fit_status_changed_cb(self, f, status):
        mapping = {
            fit.Fit.Status.PARSING: Activity.Status.PARSING,
            fit.Fit.Status.PARSED: Activity.Status.PARSED,
        }

        for fstatus, astatus in mapping.items():
            if status == fstatus:
                self.change_status(astatus)

        # cache a bit of information
        if status == fit.Fit.Status.PARSED:
            if self.fit.get_sport():
                # string
                self.set_config('sport', self.fit.get_sport())
                # float
                self.set_config('distance', self.fit.get_distance())
                # float
                self.set_config('elapsed_time',
                    self.fit.get_elapsed_time(triplet=False))
                # string
                self.set_config('start_time',
                    self.fit.get_start_time())

    # signals: because GObject doesn't support multiple inheritance, every
    # signal here will have to be copied into any subclass manually
    @GObject.Signal(arg_types=(int,))
    def status_changed(self, status):
        pass

    @GObject.Signal(arg_types=(int,))
    def strava_id_updated(self, status):
        # have a different signal for this and not just another Activity
        # status because we don't want to redraw the entire map widget just to
        # change the text on one button.
        pass

    # config options
    def get_config(self, key, default=None):
        if self.app.config.has_option(self.filename, key):
            return self.app.config.get(self.filename, key)
        return default

    def set_config(self, key, value):
        if not self.app.config.has_section(self.filename):
            self.app.config.add_section(self.filename)
        self.app.config.set(self.filename, key, value)
        self.app.config.save()

    # properties
    @property
    def filename(self):
        return self.antfile.filename

    @property
    def full_path(self):
        return self.antfile.path

    @property
    def downloaded(self):
        return os.path.exists(self.full_path)

    @property
    def strava_id(self):
        ret = self.get_config('strava_id')
        return ret if ret is None else int(ret)

    @strava_id.setter
    def strava_id(self, new_id):
        self.set_config('strava_id', str(new_id))
        self.emit('strava-id-updated', new_id)

    @property
    def date(self):
        if self.status == Activity.Status.PARSED:
            return self.fit.get_start_time()
        else:
            start = self.get_config('start_time')
            if start:
                return datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
            return self.antfile.save_date

    @property
    def sport(self):
        if self.status == Activity.Status.PARSED:
            return self.fit.get_sport()

        # will default to None
        return self.get_config('sport')


    # helper funcs
    def change_status(self, status):
        self.status = status
        self.emit('status-changed', status)

    @staticmethod
    def sort_func(activity1, activity2, unused=None):
        # use the antfile save date otherwise order can change depending on
        # what has been ordered
        if activity1.antfile.save_date > activity2.antfile.save_date:
            return -1
        elif activity1.antfile.save_date < activity2.antfile.save_date:
            return 1
        else:
            return 0

    def parse(self):
        # deliberately break if self.fit is None
        self.fit.parse()

    def upload(self):
        if self.uploader:
            return self.uploader

        self.uploader = strava.Uploader(self)

        def status_changed_cb(uploader, status):
            if status in (strava.Uploader.Status.DONE,
                    strava.Uploader.Status.DUPLICATE):
                self.strava_id = uploader.activity_id

            if status in (strava.Uploader.Status.DONE,
                    strava.Uploader.Status.ERROR,
                    strava.Uploader.Status.DUPLICATE):
                self.uploader = None

        self.uploader.connect('status-changed', status_changed_cb)

        return self.uploader

class ActivityRow(Gtk.ListBoxRow, Activity):

    # see comment about signals in Activity class definition
    status_changed = Activity.status_changed
    strava_id_updated = Activity.strava_id_updated

    ICON_SIZE = Gtk.IconSize.DND

    def __init__(self, window, app, antfile):
        Gtk.ListBoxRow.__init__(self)
        Activity.__init__(self, app, antfile)

        self.window = window

        grid = Gtk.Grid(margin=6)
        grid.set_column_spacing(10)
        self.add(grid)

        self.image = Gtk.Image(icon_name='preferences-system-time-symbolic',
            icon_size=self.ICON_SIZE)

        self.label = Gtk.Label()
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.set_valign(Gtk.Align.CENTER)
        self.label.set_halign(Gtk.Align.START)

        self.spinner = Gtk.Spinner()
        self.spinner.set_valign(Gtk.Align.CENTER)
        self.spinner.set_halign(Gtk.Align.END)
        self.spinner.set_hexpand(True)
        self.spinner.set_no_show_all(True)

        self.selector_button = Gtk.CheckButton()
        self.selector_button.set_valign(Gtk.Align.CENTER)
        self.selector_button.set_halign(Gtk.Align.END)
        self.selector_button.set_hexpand(True)
        self.selector_button.set_no_show_all(True)

        grid.attach(self.image, 0, 0, 1, 1)
        grid.attach(self.label, 1, 0, 1, 1)
        grid.attach(self.spinner, 2, 0, 1, 1)
        # don't show spinner yet
        grid.attach(self.selector_button, 3, 0, 1, 1)
        # don't show selector button yet

        if not self.downloaded:
            self.label.set_sensitive(False)
            self.image.set_from_icon_name('emblem-important-symbolic', self.ICON_SIZE)
        elif self.status == Activity.Status.DOWNLOADING:
            self.spinner.show()
            self.spinner.start()
            self.label.set_sensitive(False)
            self.image.set_from_icon_name('folder-download-symbolic', self.ICON_SIZE)

        self.connect('status-changed', self.status_changed_cb)
        self.status_changed_cb(self, self.status)

    def upload_to_strava(self):
        dialog = UploadDialog(self)
        dialog.set_transient_for(self.window)
        dialog.show_all()

    def status_changed_cb(self, activity, status):
        # TODO: change format
        self.date_str = self.date.strftime('%A %d %b %Y')
        self.time_str = self.date.strftime('%H:%M')
        markup = '<b>{}</b>\n<small>{}</small>'.format(self.date_str, self.time_str)
        self.label.set_markup(markup)

        # TODO: use some sensible icons here
        icons = {
            'swimming': 'weather-fog',
            'cycling': 'media-optical-cd-audio',
            'running': 'network-transmit-receive'
        }
        if self.sport in icons:
            self.image.set_from_icon_name('{}-symbolic'.format(icons[self.sport]),
                self.ICON_SIZE)

class UploadDialog(Gtk.Dialog):
    def __init__(self, activity):
        Gtk.Dialog.__init__(self)

        self.activity = activity

        self.set_title('Upload activity')
        self.set_modal(True)
        self.set_size_request(500, -1)

        content = self.get_content_area()

        self.label = Gtk.Label()
        self.label.set_markup('<i>Uploading...</i>')
        self.label.set_halign(Gtk.Align.START)
        content.pack_start(self.label, True, True, 0)

        self.progress = Gtk.ProgressBar()
        content.pack_start(self.progress, True, True, 5)

        def pulse():
            self.progress.pulse()
            return True
        self.pulse_id = GLib.timeout_add(100, pulse)

        self.uploader = activity.upload()
        self.uploader.connect('status-changed', self.status_changed_cb)
        self.uploader.start()

    def status_changed_cb(self, uploader, status):
        if status == strava.Uploader.Status.WAITING:
            self.label.set_markup('<i>Waiting for Strava to process activity...</i>')
        elif status == strava.Uploader.Status.DONE:
            self.close('Uploaded successfully.')
        elif status == strava.Uploader.Status.ERROR:
            self.close('Failed to upload: {}'.format(uploader.error))
        elif status == strava.Uploader.Status.DUPLICATE:
            self.close('Failed to upload: activity already uploaded.')

    def close(self, message):
        GLib.source_remove(self.pulse_id)

        self.progress.set_fraction(1.0)
        self.label.set_markup('<i>{}</i>'.format(message))

        GLib.timeout_add_seconds(2, self.destroy)

class StravaAuthDialog(Gtk.Dialog):
    def __init__(self, app):
        Gtk.Dialog.__init__(self)

        self.app = app

        headerbar = Gtk.HeaderBar()
        headerbar.set_title('Authorize Strava')
        headerbar.get_style_context().add_class(Gtk.STYLE_CLASS_TITLEBAR)
        self.set_titlebar(headerbar)

        close_button = Gtk.Button(label='Cancel')
        close_button.connect('clicked', self.close_clicked_cb)
        headerbar.pack_end(close_button)

        self.set_modal(True)
        self.set_size_request(600, 600)

        content = self.get_content_area()

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC)
        content.pack_start(scrolled, True, True, 0)

        view = WebKit.WebView()
        view.load_uri(strava.AUTH_URL)
        view.connect('notify::load-status', self.load_status_cb)

        scrolled.add(view)

    def close_clicked_cb(self, button):
        self.emit('response', Gtk.ResponseType.CANCEL)

    def load_status_cb(self, view, pspec):
        status = view.get_load_status()

        if status == WebKit.LoadStatus.FINISHED:
            uri = view.get_uri()

            if not uri.startswith(strava.CALLBACK_URL):
                return

            frame = view.get_focused_frame()
            source = frame.get_data_source()
            raw = source.get_data().str

            if raw.startswith('An error occurred'):
                self.emit('response', Gtk.ResponseType.REJECT)
            else:
                data = json.loads(raw)

                token = data.get('access_token')

                if token:
                    if not self.app.config.has_section('strava'):
                        self.app.config.add_section('strava')
                    self.app.config.set('strava', 'access_token', token)
                    self.app.config.save()

                    self.emit('response', Gtk.ResponseType.ACCEPT)

class ActivityMissingDetails(Gtk.Grid):
    def __init__(self, activity):
        Gtk.Grid.__init__(self)

        self.activity = activity

        self.set_row_spacing(12)
        self.set_column_spacing(16)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_property('margin', 24)

        image = Gtk.Image(icon_name='emblem-important-symbolic', icon_size=Gtk.IconSize.DIALOG)
        self.attach(image, 0, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_margin_left(6)
        label.set_property('xalign', 0.0)
        label.set_markup('<span font="16">' + self.activity.date_str + '</span>')
        self.attach(label, 1, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_property('xalign', 0.0)
        label.set_markup('<span font="16">' + self.activity.time_str + '</span>')
        self.attach(label, 2, 0, 1, 1)

        label = Gtk.Label('This activity is on your device but hasn\'t been downloaded to ' + \
                          'your computer yet. ' + \
                          'To view its details and upload it you must download it first.')
        label.set_property('xalign', 0.0)
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        self.attach(label, 0, 1, 3, 1)

        button = Gtk.Button('Download now')
        button.get_style_context().add_class(Gtk.STYLE_CLASS_RAISED)
        button.set_focus_on_click(False)
        self.attach(button, 0, 2, 3, 1)

class NoActivities(Gtk.Grid):
    def __init__(self):
        Gtk.Grid.__init__(self)

        self.set_row_spacing(12)
        self.set_column_spacing(16)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_property('margin', 24)

        image = Gtk.Image(icon_name='input-gaming-symbolic', icon_size=Gtk.IconSize.DIALOG)
        self.attach(image, 0, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_margin_left(6)
        label.set_property('xalign', 0.0)
        label.set_markup('<span font="16">No activities</span>')
        self.attach(label, 1, 0, 1, 1)


        label = Gtk.Label('There are currently no activities on your device.' +
                          'Go for a run, ride, or swim and then come back!')
        label.set_property('xalign', 0.0)
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        self.attach(label, 0, 1, 2, 1)

class ActivityDownloadingDetails(Gtk.Box):
    def __init__(self, activity):
        Gtk.Box.__init__(self)

        self.activity = activity

        self.set_orientation(Gtk.Orientation.VERTICAL)

        grid = Gtk.Grid()
        grid.set_row_spacing(12)
        grid.set_column_spacing(16)
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        grid.set_hexpand(True)
        grid.set_vexpand(True)
        grid.set_property('margin', 24)
        self.pack_start(grid, True, True, 0)

        image = Gtk.Image(icon_name='folder-download-symbolic', icon_size=Gtk.IconSize.DIALOG)
        grid.attach(image, 0, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_margin_left(6)
        label.set_property('xalign', 0.0)
        label.set_markup('<span font="16">' + self.activity.date_str + '</span>')
        grid.attach(label, 1, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_property('xalign', 0.0)
        label.set_markup('<span font="16">' + self.activity.time_str + '</span>')
        grid.attach(label, 2, 0, 1, 1)

        label = Gtk.Label('This activity is on your device but needs to be downloaded before its ' + \
                          'details can be shown.')
        label.set_property('xalign', 0.0)
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        grid.attach(label, 0, 1, 3, 1)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        grid.attach(box, 0, 2, 3, 1)

        label = Gtk.Label('')
        label.set_markup('<i>Waiting to download...</i>')
        label.set_property('xalign', 0.0)
        box.pack_start(label, False, False, 3)

        progress = Gtk.ProgressBar()
        progress.pulse()
        box.pack_start(progress, False, False, 0)

        def pulse():
            progress.pulse()
            return True
        GLib.timeout_add(100, pulse)

        bar = Gtk.ActionBar()
        self.pack_start(bar, False, False, 0)

        button = Gtk.Button('Cancel download')
        bar.pack_end(button)

class ActivityDetails(Gtk.ScrolledWindow):
    def __init__(self, activity):
        Gtk.ScrolledWindow.__init__(self)

        self.activity = activity

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(box)

        grid = Gtk.Grid()
        grid.set_row_spacing(12)
        grid.set_column_spacing(16)
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        grid.set_hexpand(True)
        grid.set_vexpand(True)
        grid.set_property('margin', 24)
        grid.set_focus_vadjustment(self.get_vadjustment());
        box.pack_start(grid, True, True, 0)

        # the GtkViewport has now been created
        viewport = self.get_child()
        viewport.get_style_context().add_class('view')
        viewport.get_style_context().add_class('contacts-main-view')

        image = Gtk.Image(icon_name='preferences-system-time-symbolic', icon_size=Gtk.IconSize.DIALOG)
        grid.attach(image, 0, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_margin_left(6)
        label.set_property('xalign', 0.0)
        grid.attach(label, 1, 0, 1, 1)
        self.distance_label = label

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_property('xalign', 0.0)
        grid.attach(label, 2, 0, 1, 1)
        self.elapsed_time_label = label

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_margin_left(6)
        label.set_property('xalign', 0.0)
        grid.attach(label, 1, 1, 1, 1)
        self.elevation_label = label

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_property('xalign', 0.0)
        grid.attach(label, 2, 1, 1, 1)
        self.moving_time_label = label

        # map overlay
        self.embed = GtkChamplain.Embed()
        grid.attach(self.embed, 0, 2, 3, 1)
        self.embed.show_all()

        # action bar
        bar = Gtk.ActionBar()
        box.pack_start(bar, False, False, 0)

        self.upload_button = Gtk.Button('Upload to Strava')
        if self.activity.strava_id:
            self.upload_button.set_label('View activity on Strava')
        bar.pack_end(self.upload_button)
        self.upload_button.connect('clicked', self.upload_view_clicked_cb)
        self.activity.connect('strava-id-updated', self.strava_id_updated_cb)

        # once parsed fill in the blanks
        self.fill_details()

    def upload_view_clicked_cb(self, data=None):
        if self.activity.strava_id:
            url = strava.ACTIVITY_URL.format(self.activity.strava_id)
            Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
        else:
            if self.activity.app.config.has_option('strava', 'access_token'):
                self.activity.upload_to_strava()
            else:
                dialog = StravaAuthDialog(self.activity.app)
                dialog.connect('response', self.auth_dialog_response_cb)
                dialog.set_transient_for(self.activity.window)
                dialog.show_all()

    def strava_id_updated_cb(self, activity, new_id):
        if self.activity.strava_id:
            self.upload_button.set_label('View activity on Strava')

    def auth_dialog_response_cb(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            self.activity.upload_to_strava()

        dialog.destroy()

        if response_id == Gtk.ResponseType.REJECT:
            message = Gtk.MessageDialog(self.activity.window, Gtk.DialogFlags.MODAL,
                Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE,
                'Failed to authenticate with Strava.')
            message.connect('response', lambda *x: message.destroy())
            message.show_all()

    def fill_details(self):

        def status_changed_cb(activity, status=Activity.Status.PARSED):
            if status != Activity.Status.PARSED:
                return

            f = activity.fit

            layer = Champlain.PathLayer()

            for message in f.records():
                vals = message.get_values()
                try:
                    coord = Champlain.Coordinate.new_full(
                        vals['position_lat'],
                        vals['position_long'])
                    layer.add_node(coord)
                except KeyError:
                    continue

            if layer.get_nodes():
                view = self.embed.get_view()
                view.add_layer(layer)
                view.ensure_layers_visible(True)
                view.set_property('zoom-level', 13)
            else:
                self.embed.destroy()

            # now labels
            self.distance_label.set_markup('<span font="16">{0:.1f} km</span>\n' \
                '<span color="gray">Distance</span>'.format(f.get_distance() / 1000))

            hours, mins, secs = f.get_elapsed_time()
            self.elapsed_time_label.set_markup('<span font="16">{0}:{1:02d}:{2:02d}</span>\n' \
                '<span color="gray">Elapsed Time</span>'.format(hours, mins, secs))

            elevation = f.get_elevation()
            self.elevation_label.set_markup('{}m\n' \
                '<span color="gray">Elevation</span>'.format(elevation))

            hours, mins, secs = f.get_moving_time()
            self.moving_time_label.set_markup('{0}:{1:02d}:{2:02d}\n' \
                '<span color="gray">Moving Time</span>'.format(hours, mins, secs))

        if self.activity.status == Activity.Status.PARSED:
            status_changed_cb(self.activity)
        else:
            self.activity.connect('status-changed', status_changed_cb)
            self.activity.parse()
