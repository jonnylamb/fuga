import random

from gi.repository import GtkClutter
GtkClutter.init([])
from gi.repository import Gtk, GLib, Gio, Pango, Gdk, GtkChamplain

class Window(Gtk.ApplicationWindow):
    def __init__(self):
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

        for activity in self.pane.activity_list.activities:
            activity.selector_button.connect('toggled', self.activity_toggled_cb)

        # keep left pane and toolbar the same width
        hsize_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        hsize_group.add_widget(self.left_toolbar)
        hsize_group.add_widget(self.pane)

        self.content = NoActivities()
        self.hbox.pack_start(self.content, True, True, 0)

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

            for activity in self.pane.activity_list.activities:
                activity.selector_button.show()
                activity.selector_button.set_hexpand(not activity.spinner.get_visible())

            self.left_toolbar.set_title('Select')

            self.delete_button.hide()
            self.pane.revealer.set_reveal_child(True)

        else:
            self.left_toolbar.get_style_context().remove_class('selection-mode')
            self.right_toolbar.get_style_context().remove_class('selection-mode')

            for activity in self.pane.activity_list.activities:
                activity.selector_button.hide()
                activity.selector_button.set_active(False)

            self.num_selected = 0

            self.left_toolbar.set_title('All activities')

            row = self.pane.activity_list.get_selected_row()
            if row.status == ActivityRow.Status.DOWNLOADED:
                self.delete_button.show()

            self.pane.revealer.set_reveal_child(False)

    def row_selected_cb(self, activity_list, row):
        if not row:
            return

        self.hbox.remove(self.content)

        if row.status == ActivityRow.Status.DOWNLOADED:
            self.content = Activity()
            self.delete_button.show()
        elif row.status == ActivityRow.Status.DOWNLOADING:
            self.content = ActivityDownloading()
            self.delete_button.hide()
        elif row.status == ActivityRow.Status.MISSING:
            self.content = ActivityMissing()
            self.delete_button.hide()

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

        color = Gdk.RGBA()
        color.parse('#ebebed')
        self.override_background_color(0, color)

        label = Gtk.Label('No activities')
        self.set_placeholder(label)
        label.show()

        self.activities = []
        for i in ['2013-11-27_20-45-22_4_1',
                  '2013-11-27_21-45-22_4_1',
                  '2013-12-02_22-50-40_4_2',
                  '2013-12-02_23-50-40_4_2',
                  '2013-12-04_22-53-38_4_3',
                  '2013-12-04_23-53-38_4_3',
                  '2013-12-06_18-44-34_4_4',
                  '2013-12-06_19-44-34_4_4',
                  '2013-12-09_22-30-10_4_5',
                  '2013-12-09_23-30-10_4_5',
                  '2013-12-11_21-31-46_4_6',
                  '2013-12-11_22-31-46_4_6',
                  '2013-12-22_12-20-30_4_7',
                  '2013-12-22_13-20-30_4_7',
                  '2013-12-24_15-49-44_4_8',
                  '2013-12-24_16-49-44_4_8',
                  '2013-12-27_12-13-40_4_9',
                  '2013-12-27_13-13-40_4_9',
                  '2014-01-02_10-33-56_4_10',
                  '2014-01-02_11-33-56_4_10',
                  '2014-01-04_12-08-40_4_11',
                  '2014-01-04_13-08-40_4_11',
                  '2014-01-10_13-23-28_4_12',
                  '2014-01-10_14-23-28_4_12',
                  '2014-01-12_11-28-16_4_13',
                  '2014-01-12_12-28-16_4_13',
                  '2014-01-13_21-28-02_4_14',
                  '2014-01-13_21-52-40_4_15',
                  '2014-01-16_09-31-40_4_16',
                  '2014-01-16_10-46-22_4_17',
                  '2014-01-17_10-56-26_4_18',
                  '2014-01-17_18-47-38_4_19',
                  '2014-01-18_23-51-44_4_20',
                  '2014-01-20_13-37-42_4_21',
                  '2014-01-20_13-37-44_4_22',
                  '2014-01-20_13-37-46_4_23',
                  '2014-01-20_13-37-48_4_24',
                  '2014-01-20_13-37-50_4_25',
                  '2014-01-20_13-37-52_4_26',
                  '2014-01-20_13-37-52_4_27',
                  '2014-01-21_10-47-20_4_28',
                  '2014-01-23_21-02-22_4_29',
                  '2014-01-25_11-39-50_4_30',
                  '2014-01-25_16-35-26_4_31',
                  '2014-01-27_11-49-02_4_32',
                  '2014-01-29_10-02-24_4_33',
                  '2014-01-30_22-34-32_4_34',
                  '2014-02-02_22-18-36_4_35',
                  '2014-02-03_16-24-16_4_36',
                  '2014-02-04_16-14-48_4_37',
                  '2014-02-05_13-59-28_4_38',
                  '2014-02-05_17-08-52_4_39',
                  '2014-02-06_15-50-08_4_40',
                  '2014-02-07_18-19-46_4_41']:
            row = ActivityRow(i)
            self.prepend(row)

            self.activities.append(row)

    def update_header(self, row, before_row, unused):
        current = row.get_header()

        if before_row and (not current or current is not Gtk.Separator):
            row.set_header(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        else:
            row.set_header(None)

class ActivityRow(Gtk.ListBoxRow):
    # TODO
    class Status:
        DOWNLOADED = 0
        DOWNLOADING = 1
        MISSING = 2

    def __init__(self, title):
        Gtk.ListBoxRow.__init__(self)

        grid = Gtk.Grid(margin=6)
        grid.set_column_spacing(10)
        self.add(grid)

        # TODO
        image = Gtk.Image(icon_name='preferences-system-time-symbolic', icon_size=Gtk.IconSize.DND)

        (self.date_str, self.time_str) = title.split('_')[0:2]
        self.time_str = self.time_str.replace('-', ':')
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

        # TODO
        self.status = random.randint(0, 2)
        if self.status == ActivityRow.Status.DOWNLOADED:
            pass # already done
        elif self.status == ActivityRow.Status.DOWNLOADING:
            self.spinner.show()
            self.spinner.start()
            label.set_sensitive(False)
            image.destroy()
            image = Gtk.Image(icon_name='folder-download-symbolic', icon_size=Gtk.IconSize.DND)
            grid.attach(image, 0, 0, 1, 1)
        elif self.status == ActivityRow.Status.MISSING:
            label.set_sensitive(False)
            image.destroy()
            image = Gtk.Image(icon_name='emblem-important-symbolic', icon_size=Gtk.IconSize.DND)
            grid.attach(image, 0, 0, 1, 1)

class ActivityMissing(Gtk.Grid):
    def __init__(self):
        Gtk.Grid.__init__(self)

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
        label.set_markup('<span font="16">2014-02-07</span>')
        self.attach(label, 1, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_property('xalign', 0.0)
        label.set_markup('<span font="16">18:19:46</span>')
        self.attach(label, 2, 0, 1, 1)

        label = Gtk.Label('This activity is on your device but hasn\'t been downloaded yet. ' + \
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
        label.set_markup('<span font="16">2014-02-07</span>')
        grid.attach(label, 1, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_property('xalign', 0.0)
        label.set_markup('<span font="16">18:19:46</span>')
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
    def __init__(self):
        Gtk.ScrolledWindow.__init__(self)

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
        label.set_markup('<span font="16">2014-02-07</span>')
        grid.attach(label, 1, 0, 1, 1)

        label = Gtk.Label('')
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_property('xalign', 0.0)
        label.set_markup('<span font="16">18:19:46</span>')
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

