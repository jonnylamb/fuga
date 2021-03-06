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

import json

# for champlain
from gi.repository import GtkClutter
GtkClutter.init([])

from gi.repository import Gtk, GLib, Pango, Gdk, GtkChamplain, Champlain, WebKit

from activity import Activity
import strava

class Activities(Gtk.Bin):
    def __init__(self, app):
        Gtk.Bin.__init__(self)

        self.app = app

        # content box
        self.hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL, 0)
        self.add(self.hbox)

        # activity list pane
        self.pane = ListPane()
        self.hbox.pack_start(self.pane, False, False, 0)
        self.pane.set_size_request(300, -1)

        self.pane.activity_list.connect('row-selected', self.row_selected_cb)

        self.content = NoActivities()
        self.hbox.pack_start(self.content, True, True, 0)

    def set_header(self, header):
        # ugly but for convenience
        self.header = header

        self.num_selected = 0
        self.header.select_button.connect('toggled', self.select_toggled_cb)
        self.header.delete_button.connect('clicked', self.delete_clicked_cb)

        # keep left pane and toolbar the same width
        hsize_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        hsize_group.add_widget(self.header.left_toolbar)
        hsize_group.add_widget(self.pane)

    def add_activity(self, antfile):
        row = ActivityRow(self, self.app, antfile)
        row.selector_button.connect('toggled', self.activity_toggled_cb)
        self.pane.activity_list.prepend(row)

        # not at all necessary to enable unless the listview row starts
        # showing actual details about the activity
        #self.parse_all()

        self.header.select_button.set_sensitive(True)

    def select_first(self):
        activity = self.pane.activity_list.get_row_at_index(0)
        if activity:
            self.pane.activity_list.select_row(activity)

    def parse_all(self, unused=None):
        def idle():
            for activity in self.pane.activity_list.get_children():
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
            self.header.left_toolbar.set_title('{} selected'.format(self.num_selected))
            self.pane.delete_button.set_sensitive(True)
        else:
            self.header.left_toolbar.set_title('Select')
            self.pane.delete_button.set_sensitive(False)

    def select_toggled_cb(self, toggle_button):
        if toggle_button.get_active():
            self.header.left_toolbar.get_style_context().add_class('selection-mode')
            self.header.right_toolbar.get_style_context().add_class('selection-mode')

            for activity in self.pane.activity_list.get_children():
                activity.selector_button.show()
                activity.selector_button.set_hexpand(not activity.spinner.get_visible())

            self.header.left_toolbar.set_title('Select')

            self.header.delete_button.hide()
            self.pane.revealer.set_reveal_child(True)

            self.header.right_toolbar.set_show_close_button(False)

        else:
            self.header.left_toolbar.get_style_context().remove_class('selection-mode')
            self.header.right_toolbar.get_style_context().remove_class('selection-mode')

            for activity in self.pane.activity_list.get_children():
                activity.selector_button.hide()
                activity.selector_button.set_active(False)

            self.num_selected = 0

            self.header.left_toolbar.set_title('All activities')

            activity = self.pane.activity_list.get_selected_row()
            if activity:
                self.header.delete_button.set_visible(
                    activity.status == Activity.Status.NONE or
                    activity.status == Activity.Status.PARSED)
            else:
                self.header.delete_button.hide()

            self.pane.revealer.set_reveal_child(False)

            self.header.right_toolbar.set_show_close_button(True)

    def delete_clicked_cb(self, button):
        activity = self.pane.activity_list.get_selected_row()
        activity.delete()

    def row_selected_cb(self, activity_list, activity):
        # don't keep parsing activities when the app is closing.
        # GtkListBox will remove each item in the list and so will
        # cause row-selected to be fired each time.
        if activity and activity.window.in_destruction():
            return

        if activity:
            self.reset_content(activity)
        else:
            activity = self.pane.activity_list.get_row_at_index(self.selected)
            if activity:
                self.pane.activity_list.select_row(activity)
                activity.changed()

    def activity_status_changed_cb(self, activity, status):
        self.reset_content(activity)

    def reset_content(self, activity):
        if self.content:
            self.content.destroy()
            self.content = None

        if not activity:
            return

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

        # failed to parse
        elif activity.status in (Activity.Status.DOWNLOAD_FAILED,
                                 Activity.Status.PARSE_FAILED):
            self.content = ActivityFailed(activity)

        # just deleted
        elif activity.status == Activity.Status.DELETED:
            self.pane.activity_list.remove(activity)
            return

        self.header.delete_button.set_visible(
            activity.status == Activity.Status.NONE or
            (activity.status == Activity.Status.PARSED and \
            not self.header.select_button.get_active()))

        self.hbox.pack_start(self.content, True, True, 0)
        self.content.show_all()

        title = activity.date.strftime('%A %d %B at %H:%M')
        self.header.right_toolbar.set_title(title)

        # save the index of the current activity so if we delete this
        # activity, we can jump to the next activity in the list (which will
        # have the same index that we're saving now)
        self.selected = activity.get_index()

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

class ActivitiesHeader(Gtk.Box):
    def __init__(self, page):
        Gtk.Box.__init__(self)

        # left toolbar
        self.left_toolbar = Gtk.HeaderBar()
        self.left_toolbar.set_title('All activities')
        self.left_toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_TITLEBAR)
        self.left_toolbar.get_style_context().add_class('contacts-left-header-bar')
        self.pack_start(self.left_toolbar, False, False, 0)

        # back button
        self.back_button = Gtk.Button.new_from_icon_name('go-previous-symbolic',
            Gtk.IconSize.MENU)
        self.left_toolbar.pack_start(self.back_button)

        # select button
        self.select_button = Gtk.ToggleButton()
        self.select_button.set_focus_on_click(False)
        self.select_button.set_sensitive(False)
        image = Gtk.Image(icon_name='object-select-symbolic', icon_size=Gtk.IconSize.MENU)
        self.select_button.set_image(image)
        self.left_toolbar.pack_end(self.select_button)

        # right toolbar
        self.right_toolbar = Gtk.HeaderBar()
        self.right_toolbar.set_show_close_button(True)
        self.right_toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_TITLEBAR)
        self.right_toolbar.get_style_context().add_class('contacts-right-header-bar')
        self.pack_start(self.right_toolbar, True, True, 0)

        # delete button
        self.delete_button = Gtk.Button(label='Delete')
        self.delete_button.get_style_context().add_class('destructive-action')
        self.delete_button.set_no_show_all(True)
        self.right_toolbar.pack_end(self.delete_button)

        # keep all menu buttons the same height
        vsize_group = Gtk.SizeGroup(Gtk.SizeGroupMode.VERTICAL)
        vsize_group.add_widget(self.select_button)
        vsize_group.add_widget(self.delete_button)

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

class ActivityRow(Gtk.ListBoxRow, Activity):

    # see comment about signals in Activity class definition
    status_changed = Activity.status_changed
    strava_id_updated = Activity.strava_id_updated
    download_progress = Activity.download_progress

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
            self.image.set_from_icon_name('dialog-question-symbolic', self.ICON_SIZE)

        self.connect('status-changed', self.status_changed_cb)
        self.status_changed_cb(self, self.status)

    def set_image_from_sport(self, image, size):
        # TODO: use some sensible icons here
        if self.sport == 'swimming':
            image.set_from_icon_name('weather-fog-symbolic', size)
        elif self.sport == 'cycling':
            image.set_from_file('ui/ic_directions_bike_48px.svg')
        elif self.sport == 'running':
            image.set_from_file('ui/ic_directions_walk_48px.svg')
        else:
            image.set_from_icon_name('preferences-system-time-symbolic', size)

    def status_changed_cb(self, activity, status):
        downloading = (status == Activity.Status.DOWNLOADING)
        self.spinner.set_visible(downloading)
        self.spinner.set_property('active', downloading)

        if downloading:
            self.image.set_from_icon_name('folder-download-symbolic', self.ICON_SIZE)
            return
        elif status == Activity.Status.DELETED:
            return
        elif status == Activity.Status.DOWNLOADED:
            self.label.set_sensitive(True)
        elif status == Activity.Status.DOWNLOAD_FAILED:
            self.image.set_from_icon_name('dialog-error-symbolic', self.ICON_SIZE)

        # TODO: change format
        self.date_str = self.date.strftime('%A %d %b %Y')
        self.time_str = self.date.strftime('%H:%M')
        markup = '{}\n<small>{}</small>'.format(self.date_str, self.time_str)
        self.label.set_markup(markup)

        if not self.downloaded:
            return

        self.set_image_from_sport(self.image, self.ICON_SIZE)

        self.changed()

class UploadInfoBar(Gtk.InfoBar):
    def __init__(self):
        Gtk.InfoBar.__init__(self)

        self.uploader = None
        self.status_changed_id = 0

        self.set_no_show_all(True)
        self.connect('response', self.response_cb)
        self.uploader = None

        content = self.get_content_area()

        hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL, 0)
        hbox.show()
        content.add(hbox)

        self.spinner = Gtk.Spinner()
        self.spinner.set_margin_right(8)
        self.spinner.show()
        hbox.pack_start(self.spinner, False, False, 0)

        self.image = Gtk.Image()
        self.image.set_margin_right(8)
        self.image.hide()
        hbox.pack_start(self.image, False, False, 0)

        self.label = Gtk.Label('Uploading...')
        self.label.show()
        hbox.pack_start(self.label, True, True, 0)

        self.button = self.add_button('Close', Gtk.ResponseType.CLOSE)
        self.button.set_sensitive(False)

    def start(self, uploader):
        if self.uploader and self.status_changed_id:
            self.uploader.disconnect(self.status_changed_id)

        self.uploader = uploader
        self.status_changed_id = uploader.connect('status-changed', self.status_changed_cb)

        self.image.hide()

        self.spinner.show()
        self.spinner.start()
        self.show()

        # just in case the upload is already ongoing
        self.status_changed_cb(uploader, uploader.status)

    def status_changed_cb(self, uploader, status):
        icon_name = 'dialog-error-symbolic'
        if status == strava.Uploader.Status.UPLOADING:
            self.label.set_text('Uploading...')
            return
        if status == strava.Uploader.Status.WAITING:
            self.label.set_text('Waiting for Strava to process activity...')
            return
        elif status == strava.Uploader.Status.DONE:
            self.label.set_text('Uploaded successfully.')
            icon_name = 'emblem-ok-symbolic'
        elif status == strava.Uploader.Status.ERROR:
            self.label.set_text('Failed to upload: {}'.format(uploader.error))
        elif status == strava.Uploader.Status.DUPLICATE:
            self.label.set_text('Failed to upload: activity already uploaded.')
        elif status == strava.Uploader.Status.AUTH_ERROR:
            self.label.set_text('Failed to authenticate with Strava; try again.')
        else:
            return

        self.button.set_sensitive(True)

        self.spinner.stop()
        self.spinner.hide()

        self.image.set_from_icon_name(icon_name, Gtk.IconSize.MENU)
        self.image.show()

    def response_cb(self, infobar, response):
        if response != Gtk.ResponseType.CLOSE:
            return

        self.hide()

        if self.uploader:
            self.uploader.disconnect_by_func(self.status_changed_cb)
            self.uploader = None

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
        self.set_size_request(800, 800)

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
                else:
                    self.emit('response', Gtk.ResponseType.REJECT)

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

        image = Gtk.Image(icon_name='dialog-question-symbolic', icon_size=Gtk.IconSize.DIALOG)
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

        button.connect('clicked', self.download_clicked_cb)

    def download_clicked_cb(self, button):
        self.activity.download()

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


        label = Gtk.Label('There are currently no activities on your device. ' +
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

        self.label = Gtk.Label('')
        self.label.set_markup('<i>Waiting to download...</i>')
        self.label.set_property('xalign', 0.0)
        box.pack_start(self.label, False, False, 3)

        self.progress = Gtk.ProgressBar()
        box.pack_start(self.progress, False, False, 0)

        def pulse():
            self.progress.pulse()
            return True
        self.pulse_timeout_id = GLib.timeout_add(100, pulse)

        # TODO: we can't actually cancel these downloads though
        #bar = Gtk.ActionBar()
        #self.pack_start(bar, False, False, 0)

        #button = Gtk.Button('Cancel download')
        #bar.pack_end(button)

        self.activity.connect('download-progress', self.download_progress_cb)

    def download_progress_cb(self, activity, fraction):
        if self.pulse_timeout_id:
            GLib.source_remove(self.pulse_timeout_id)
            self.pulse_timeout_id = 0

        self.progress.set_fraction(fraction)
        self.label.set_markup('<i>Downloading...</i>')

class ActivityFailed(Gtk.Grid):
    def __init__(self, activity):
        Gtk.Grid.__init__(self)

        self.activity = activity

        self.set_row_spacing(12)
        self.set_column_spacing(16)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_property('margin', 24)

        image = Gtk.Image(icon_name='dialog-error-symbolic', icon_size=Gtk.IconSize.DIALOG)
        self.attach(image, 0, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_margin_left(6)
        label.set_property('xalign', 0.0)
        if activity.status == Activity.Status.PARSE_FAILED:
            title = 'Failed to parse file'
        else:
            title = 'Failed to download file'
        label.set_markup('<span font="16">{}</span>'.format(title))
        self.attach(label, 1, 0, 1, 1)

        label = Gtk.Label()
        if activity.status == Activity.Status.PARSE_FAILED:
            markup = 'The file <tt>{}</tt> could not be parsed.'.format(activity.full_path)
        elif activity.status == Activity.Status.DOWNLOAD_FAILED:
            markup  = 'The activity failed to download. You can try again.'

        label.set_markup(markup)
        label.set_property('xalign', 0.0)
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        self.attach(label, 0, 1, 2, 1)

        button = Gtk.Button('Download')
        button.get_style_context().add_class(Gtk.STYLE_CLASS_RAISED)
        button.set_focus_on_click(False)
        self.attach(button, 0, 2, 3, 1)

        button.connect('clicked', self.download_clicked_cb)

    def download_clicked_cb(self, button):
        self.activity.download()

class ActivityDetails(Gtk.Box):
    def __init__(self, activity):
        Gtk.Box.__init__(self)

        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.get_style_context().add_class('view')
        self.get_style_context().add_class('contacts-main-view')

        self.activity = activity

        self.infobar = UploadInfoBar()
        self.pack_start(self.infobar, False, False, 0)

        grid = Gtk.Grid()
        grid.set_row_spacing(12)
        grid.set_column_spacing(16)
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        grid.set_hexpand(True)
        grid.set_vexpand(True)
        grid.set_property('margin', 24)
        self.pack_start(grid, True, True, 0)

        image = Gtk.Image()
        activity.set_image_from_sport(image, Gtk.IconSize.DIALOG)
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
        self.pack_start(bar, False, False, 0)

        self.upload_button = Gtk.Button('Upload to Strava')
        self.strava_id_updated_cb(None, None)
        bar.pack_end(self.upload_button)
        self.upload_button.connect('clicked', self.upload_view_clicked_cb)
        self.activity.connect('strava-id-updated', self.strava_id_updated_cb)

        # once parsed fill in the blanks
        self.fill_details()

    def upload_view_clicked_cb(self, button):
        if self.activity.strava_id:
            url = strava.ACTIVITY_URL.format(self.activity.strava_id)
            Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
        else:
            config = self.activity.app.config

            if config.has_option('strava', 'access_token') and \
               config.get('strava', 'access_token'):

                uploader = self.activity.upload()
                uploader.start()
                uploader.connect('status-changed', self.uploader_status_changed_cb)

                self.infobar.start(uploader)
                button.set_sensitive(False)

            else:
                dialog = StravaAuthDialog(self.activity.app)
                dialog.connect('response', self.auth_dialog_response_cb)
                toplevel = self.activity.window.get_toplevel()
                dialog.set_transient_for(toplevel)
                dialog.show_all()

    def uploader_status_changed_cb(self, uploader, status):
        if status == strava.Uploader.Status.AUTH_ERROR:
            self.activity.app.config.set('strava', 'access_token', '')
            self.activity.app.config.save()

        if status in (strava.Uploader.Status.DUPLICATE,
                      strava.Uploader.Status.AUTH_ERROR):
            self.upload_button.set_sensitive(True)

    def strava_id_updated_cb(self, activity, new_id):
        if self.activity.strava_id:
            self.upload_button.set_sensitive(True)
            self.upload_button.set_label('View activity on Strava')

    def auth_dialog_response_cb(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            self.upload_view_clicked_cb(self.upload_button)

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

                # https://bugzilla.gnome.org/show_bug.cgi?id=754718
                # for some reason connecting to to ::realize on view
                # or embed isn't enough. in fact this idle only works
                # most of the time but for now it's good enough.
                view.set_zoom_level(15)
                GLib.idle_add(lambda: view.ensure_layers_visible(False))
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

            if activity.uploader is not None:
                activity.uploader.connect('status-changed',
                    lambda *x: self.strava_id_updated_cb(None, None))

                self.infobar.start(activity.uploader)
                self.infobar.connect('response',
                    lambda *x: self.strava_id_updated_cb(None, None))

                self.upload_button.set_sensitive(False)

            # end of status_changed_cb

        if self.activity.status == Activity.Status.PARSED:
            status_changed_cb(self.activity)
        else:
            self.activity.connect('status-changed', status_changed_cb)
            self.activity.parse()
