import random

from gi.repository import GtkClutter
GtkClutter.init([])
from gi.repository import Gtk, GLib, Gio, Pango, Gdk, GtkChamplain

class Window(Gtk.ApplicationWindow):
    def __init__(self, activities):
        Gtk.ApplicationWindow.__init__(self)

        self.set_default_size(1000, 600)
        self.set_title('Run')

        #  titlebar
        titlebar_box = Gtk.Box()
        self.set_titlebar(titlebar_box)

        # left toolbar
        self.left_toolbar = Gtk.HeaderBar()
        self.left_toolbar.set_title('All ativities')
        self.left_toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_TITLEBAR)
        self.left_toolbar.get_style_context().add_class('contacts-left-header-bar')
        titlebar_box.pack_start(self.left_toolbar, False, False, 0)

        # select button
        select_button = Gtk.ToggleButton()
        select_button.set_focus_on_click(False)
        image = Gtk.Image(icon_name='object-select-symbolic', icon_size=Gtk.IconSize.MENU)
        select_button.set_image(image)
        self.left_toolbar.pack_end(select_button)

        select_button.connect('toggled', self.select_toggled_cb)
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
        vsize_group.add_widget(select_button)
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

        # add activities
        self.activities = []
        for activity in activities:
            self.add_activity(activity)

    def add_activity(self, antfile):
        row = ActivityRow(antfile)
        row.selector_button.connect('toggled', self.activity_toggled_cb)
        self.pane.activity_list.prepend(row)
        self.activities.append(row)

    def activity_toggled_cb(self, selector):
        if selector.get_active():
            self.num_selected += 1
        else:
            self.num_selected -= 1

        if self.num_selected > 0:
            self.left_toolbar.set_title('%s selected' % self.num_selected)
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

        else:
            self.left_toolbar.get_style_context().remove_class('selection-mode')
            self.right_toolbar.get_style_context().remove_class('selection-mode')

            for activity in self.activities:
                activity.selector_button.hide()
                activity.selector_button.set_active(False)

            self.num_selected = 0

            self.left_toolbar.set_title('All activities')

            row = self.pane.activity_list.get_selected_row()
            if row.antfile.exists:
                self.delete_button.show()

            self.pane.revealer.set_reveal_child(False)

    def row_selected_cb(self, activity_list, row):
        if not row:
            return

        self.hbox.remove(self.content)

        if row.antfile.exists:
            self.content = Activity(row)
            self.delete_button.show()
        else:
            self.content = ActivityMissing(row)
            self.delete_button.hide()
        # elif row.status == ActivityRow.Status.DOWNLOADING:
        #     self.content = ActivityDownloading()
        #     self.delete_button.hide()

        self.hbox.pack_start(self.content, True, True, 0)
        self.content.show_all()

        self.right_toolbar.set_title(row.date_str)

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

        bar = Gtk.Toolbar()
        bar.get_style_context().add_class(Gtk.STYLE_CLASS_MENUBAR)
        bar.get_style_context().add_class('contacts-edit-toolbar')
        self.revealer.add(bar)

        # TODO
        #tool_item = Gtk.ToolItem()
        #bar.insert(tool_item, -1)
        #delete_button = Gtk.Button('Upload')
        #tool_item.add(delete_button)

        tool_item = Gtk.SeparatorToolItem()
        tool_item.set_expand(True)
        tool_item.set_draw(False)
        bar.insert(tool_item, -1)

        tool_item = Gtk.ToolItem()
        bar.insert(tool_item, -1)
        self.delete_button = Gtk.Button('Delete')
        self.delete_button.get_style_context().add_class('destructive-action')
        self.delete_button.set_sensitive(False)
        tool_item.add(self.delete_button)

class ActivityList(Gtk.ListBox):
    def __init__(self):
        Gtk.ListBox.__init__(self)

        self.set_selection_mode(Gtk.SelectionMode.BROWSE)
        self.set_header_func(self.update_header, None)
        self.set_sort_func(self.sort, None)

        color = Gdk.RGBA()
        color.parse('#ebebed')
        self.override_background_color(0, color)

        label = Gtk.Label('No activities')
        self.set_placeholder(label)
        label.show()

    def update_header(self, row, before_row, unused):
        current = row.get_header()

        if before_row and (not current or current is not Gtk.Separator):
            row.set_header(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        else:
            row.set_header(None)

    def sort(self, row1, row2, unused):
        if row1.antfile.date > row2.antfile.date:
            return -1
        elif row1.antfile.date < row2.antfile.date:
            return 1
        else:
            return 0

class ActivityRow(Gtk.ListBoxRow):
    def __init__(self, antfile):
        Gtk.ListBoxRow.__init__(self)

        self.antfile = antfile

        grid = Gtk.Grid(margin=6)
        grid.set_column_spacing(10)
        self.add(grid)

        # TODO
        image = Gtk.Image(icon_name='preferences-system-time-symbolic', icon_size=Gtk.IconSize.DND)

        self.date_str = antfile.date.strftime('%Y-%m-%d')
        self.time_str = antfile.date.strftime('%H:%M:%S')
        markup = '<b>%s</b>\n<small>%s</small>' % (self.date_str, self.time_str)

        label = Gtk.Label()
        label.set_markup(markup)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_valign(Gtk.Align.CENTER)
        label.set_halign(Gtk.Align.START)

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

        grid.attach(image, 0, 0, 1, 1)
        grid.attach(label, 1, 0, 1, 1)
        grid.attach(self.spinner, 2, 0, 1, 1)
        # don't show spinner yet
        grid.attach(self.selector_button, 3, 0, 1, 1)
        # don't show selector button yet

        if not self.antfile.exists:
            label.set_sensitive(False)
            image.destroy()
            image = Gtk.Image(icon_name='emblem-important-symbolic', icon_size=Gtk.IconSize.DND)
            grid.attach(image, 0, 0, 1, 1)
        # elif self.status == ActivityRow.Status.DOWNLOADING:
        #     self.spinner.show()
        #     self.spinner.start()
        #     label.set_sensitive(False)
        #     image.destroy()
        #     image = Gtk.Image(icon_name='folder-download-symbolic', icon_size=Gtk.IconSize.DND)
        #     grid.attach(image, 0, 0, 1, 1)

class ActivityMissing(Gtk.Grid):
    def __init__(self, row):
        Gtk.Grid.__init__(self)

        self.row = row

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
        label.set_markup('<span font="16">' + self.row.date_str + '</span>')
        self.attach(label, 1, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_property('xalign', 0.0)
        label.set_markup('<span font="16">' + self.row.time_str + '</span>')
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

class ActivityDownloading(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)

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
        label.set_markup('<span font="16">' + self.row.date_str + '</span>')
        grid.attach(label, 1, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_property('xalign', 0.0)
        label.set_markup('<span font="16">' + self.row.time_str + '</span>')
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

        # toolbar
        bar = Gtk.Toolbar()
        bar.get_style_context().add_class(Gtk.STYLE_CLASS_MENUBAR)
        bar.get_style_context().add_class('contacts-edit-toolbar')
        self.pack_start(bar, False, False, 0)

        tool_item = Gtk.SeparatorToolItem()
        tool_item.set_expand(True)
        tool_item.set_draw(False)
        bar.insert(tool_item, -1)

        tool_item = Gtk.ToolItem()
        bar.insert(tool_item, -1)
        button = Gtk.Button('Cancel download')
        tool_item.add(button)

class Activity(Gtk.ScrolledWindow):
    def __init__(self, row):
        Gtk.ScrolledWindow.__init__(self)

        self.row = row

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
        label.set_markup('<span font="16">' + self.row.date_str + '</span>')
        grid.attach(label, 1, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_property('xalign', 0.0)
        label.set_markup('<span font="16">' + self.row.time_str +'</span>')
        grid.attach(label, 2, 0, 1, 1)

        row = 1
        col = 0

        # TODO: details


        embed = GtkChamplain.Embed()
        view = embed.get_view()
        view.center_on(41.892916, 12.48252)
        view.set_property('zoom-level', 15)
        grid.attach(embed, 0, 2, 3, 1)
        embed.show_all()

        # toolbar
        bar = Gtk.Toolbar()
        bar.get_style_context().add_class(Gtk.STYLE_CLASS_MENUBAR)
        bar.get_style_context().add_class('contacts-edit-toolbar')
        box.pack_start(bar, False, False, 0)

        tool_item = Gtk.SeparatorToolItem()
        tool_item.set_expand(True)
        tool_item.set_draw(False)
        bar.insert(tool_item, -1)

        tool_item = Gtk.ToolItem()
        bar.insert(tool_item, -1)
        button = Gtk.Button('Upload')
        tool_item.add(button)

