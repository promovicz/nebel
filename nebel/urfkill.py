from __future__ import absolute_import

from nebel.dbus import *

URFKILL = "org.freedesktop.URfkill"
URFKILL_DEVICE = "org.freedesktop.URfkill.Device"

URFKILL_PATH = "/org/freedesktop/URfkill"

class RfkillDevice(DbusObject):
    def __init__(self, path):
        DbusObject.__init__(self, URFKILL, path, [URFKILL_DEVICE])
        self.name = "<unknown>"
        self.soft = False
        self.hard = False
        self.blocked = False

    def update(self):
        DbusObject.update(self)
        was_init = self.init
        was_blocked = self.blocked
        self.update_prop(URFKILL_DEVICE, "name", str)
        self.update_prop(URFKILL_DEVICE, "soft", bool)
        self.update_prop(URFKILL_DEVICE, "hard", bool)
        self.blocked = self.hard or self.soft
        is_blocked = self.blocked
        if was_init:
            if was_blocked != is_blocked:
                if is_blocked:
                    self.notify("Blocked radio %s" % self.name)
                else:
                    self.notify("Unblocked radio %s" % self.name)
        self.init = True

class RfkillMonitor(DbusObject):
    def __init__(self):
        DbusObject.__init__(self, URFKILL, URFKILL_PATH, [URFKILL])
        self.devs = dict()
        self.added()

    def added(self):
        DbusObject.added(self)
        self.enumerate()
        self.sigadd = self.obj.connect_to_signal("DeviceAdded", self.dev_added_changed)
        self.sigchg = self.obj.connect_to_signal("DeviceChanged", self.dev_added_changed)
        self.sigdel = self.obj.connect_to_signal("DeviceRemoved", self.dev_removed)

    def removed(self):
        self.sigadd.remove()
        self.sigadd = None
        self.sigchg.remove()
        self.sigchg = None
        self.sigdel.remove()
        self.sigdel = None
        DbusObject.removed(self)

    def enumerate(self):
        devs = self.obj.EnumerateDevices(dbus_interface=URFKILL)
        for dev in devs:
            self.dev_added_changed(dev)

    def dev_added_changed(self, path):
        name = str(path)
        if not name in self.devs:
            self.devs[name] = RfkillDevice(path)
        self.devs[name].update()

    def dev_removed(self, path):
        name = str(path)
        if name in self.devs:
            del self.devs[name]
