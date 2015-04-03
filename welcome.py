from gi.repository import Gtk, Pango

class WelcomeHeader(Gtk.HeaderBar):
    def __init__(self):
        Gtk.HeaderBar.__init__(self)

        self.set_show_close_button(False)

        self.close_button = Gtk.Button('Close')
        self.pack_start(self.close_button)

        self.next_button = Gtk.Button('Next')
        self.next_button.get_style_context().add_class('suggested-action')
        self.pack_end(self.next_button)

class Welcome(Gtk.Bin):
    def __init__(self, app):
        Gtk.Bin.__init__(self)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.FILL)
        self.add(box)

        image = Gtk.Image.new_from_icon_name('media-removable-symbolic', Gtk.IconSize.DND)
        image.set_margin_top(40)
        image.set_pixel_size(96)
        image.get_style_context().add_class('dim-label')
        box.pack_start(image, False, False, 0)

        label = Gtk.Label('Welcome')
        label.set_margin_top(18)
        label.set_halign(Gtk.Align.CENTER)
        label.set_valign(Gtk.Align.START)
        # TODO: set pango attributes:
        # 1. scale = 1.8
        # 2. weight = bold
        #attrs = Pango.AttrList()
        #label.set_attributes(attrs)
        box.pack_start(label, False, False, 0)

        label = Gtk.Label('Select device from which to view activities')
        label.set_margin_top(6)
        box.pack_start(label, False, False, 0)

        device_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        device_box.set_margin_top(18)
        device_box.set_margin_bottom(18)
        device_box.set_halign(Gtk.Align.CENTER)
        device_box.set_valign(Gtk.Align.START)
        box.pack_start(device_box, True, True, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        device_box.pack_start(scrolled, True, True, 0)

        listbox = Gtk.ListBox()
        listbox.set_vexpand(True)
        listbox.set_halign(Gtk.Align.FILL)
        listbox.set_valign(Gtk.Align.FILL)
        scrolled.add(listbox)

        device = AntDevice()
        listbox.add(device)

        dots = DotDotDot()
        dots.set_sensitive(False)
        listbox.add(dots)

class AntDevice(Gtk.ListBoxRow):
    def __init__(self):
        Gtk.ListBoxRow.__init__(self)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_halign(Gtk.Align.START)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        self.add(box)

        label = Gtk.Label('Garmin ANT device')
        label.set_alignment(0, 0.5)
        label.set_width_chars(40)
        box.pack_start(label, False, False, 0)

        checkmark = Gtk.Image.new_from_icon_name('object-select-symbolic', Gtk.IconSize.MENU)
        checkmark.set_margin_start(10)
        checkmark.set_margin_end(10)
        box.pack_start(checkmark, True, True, 0)

class DotDotDot(Gtk.ListBoxRow):
    def __init__(self):
        Gtk.ListBoxRow.__init__(self)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_halign(Gtk.Align.FILL)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        self.add(box)

        dots = Gtk.Image.new_from_icon_name('view-more-symbolic', Gtk.IconSize.MENU)
        box.pack_start(dots, True, True, 0)