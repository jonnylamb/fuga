Fuga
====

A GNOME application for managing activities from a Garmin device using
the ANT-FS protocol.

Dependencies
------------

* [GTK3](http://www.gtk.org/)
* [PyGObject](https://wiki.gnome.org/Projects/PyGObject)
* [libchamplain](https://wiki.gnome.org/Projects/libchamplain)
* [PyUSB](https://github.com/walac/pyusb)
* [openant](https://github.com/Tigge/openant)
* [python-fitparse](https://github.com/dtcooper/python-fitparse) (`ng` branch)

Usage
-----

With the dependencies in their appropriate path, call `./fuga`.

Setting the `FAKE_GARMIN` environment variable will make it not
connect to any Garmin device and will instead list the activities
already downloaded.

Once the activity list is showing, pick an activity on the left hand
side and see its details and map on the right hand side. Upload the
activity to Strava using the similarly named button and if you haven't
already authorized it to upload to your Strava account a dialog will
appear to help get permission.

Local storage
-------------

Device information is saved in the `$XDG_DATA_HOME/fuga/<device id>`
(`$XDG_DATA_HOME` defaults to `~/.local/share`) folder. The activity
FIT files are saved in the `activities` subfolder.

There is a small `fuga.ini` file saved in the `$XDG_CONFIG_HOME/fuga/`
folder.

Known issues
------------

* Reconnections to the device fail inside openant. This problem [has
  been filed](https://github.com/Tigge/openant/issues/14) against
  openant.

Future plans
------------

The original idea for this project was an application to be able to
create workout plans on a real computer as opposed to using the
annoyingly small and frustrating UI on the actual device. This would
be especially useful when following a, say, running plan; it would
take much less time setting up each workout on the computer than on
the device. I haven't implemented this yet as I wasn't sure what the
UI should look like.

Todo list
---------

UI:

* make loading stack page less ugly
* display activity timings in the row?
* use GtkBuilder
* work out what to do with icons
* implement multi-delete
* does deleting the last item break things? probably.
* add a desktop file
* move strava UI code out of `activities.py`
* ensure champlain zoom level is correct (!)
* make infobar go red on error
* make no activities page less ugly

Connectivity:

* add a timeout when connecting
* ensure garmin connected to on a reconnection is the same one!

Design:

* make queuing not really ugly
* add "list current items" device as `fakegarmin`
* rename `fakegarmin` to something like `dirlist` and add Edge 800 device
* make stack pages and headers link up, especially for the welcome page
