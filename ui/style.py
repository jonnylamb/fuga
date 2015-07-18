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

from gi.repository import Gtk, Gdk

# this is a ugly but I cba with GResources and loading stuff from files is
# annoying for how immature this all is

CSS = """
.contacts-main-view.view {
  background-color: mix(@theme_bg_color, @theme_base_color, 0.2);
}


/* Border on the right in the left menu toolbar */
.contacts-left-header-bar:dir(ltr) {
 border-right-width: 1px;
}

.contacts-left-header-bar:dir(rtl) {
 border-left-width: 1px;
}

.contacts-left-header-bar:dir(ltr),
.contacts-right-header-bar:dir(rtl) {
  border-top-right-radius: 0;
}

.contacts-right-header-bar:dir(ltr),
.contacts-left-header-bar:dir(rtl) {
  border-top-left-radius: 0;
}
"""

def setup():
    style_provider = Gtk.CssProvider()
    style_provider.load_from_data(CSS)

    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
