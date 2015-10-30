from __future__ import absolute_import

from enum import Enum

from nebel.dbus import *

UPOWER = "org.freedesktop.UPower"
UPOWER_DEVICE = "org.freedesktop.UPower.Device"

UPOWER_PATH = "/org/freedesktop/UPower"

class DeviceType(Enum):
    unknown = 0
    ac = 1
    battery = 2

class DeviceState(Enum):
    unknown = 0
    charging = 1
    discharging = 2
    empty = 3
    charged = 4
    pending_charge = 5
    pending_discharge = 6

class PowerDevice(DbusObject):
    def __init__(self, path):
        DbusObject.__init__(self, UPOWER, path, [UPOWER_DEVICE])
        self.Type = DeviceType.unknown
        self.PowerSupply = False
        self.State = DeviceState.unknown
        self.Online = False
        self.TimeToEmpty = 0
        self.TimeToFull = 0
        self.Percentage = 0.0

    def update(self):
        DbusObject.update(self)
        self.update_prop(UPOWER_DEVICE, "Type", DeviceType)
        self.update_prop(UPOWER_DEVICE, "PowerSupply", bool)
        self.update_prop(UPOWER_DEVICE, "State", DeviceState)
        self.update_prop(UPOWER_DEVICE, "Online", bool)
        self.update_prop(UPOWER_DEVICE, "TimeToEmpty", str)
        self.update_prop(UPOWER_DEVICE, "TimeToFull", str)
        self.update_prop(UPOWER_DEVICE, "Percentage", float)
        self.init = True

class PowerMonitor(DbusObject):
    def __init__(self):
        DbusObject.__init__(self, UPOWER, UPOWER_PATH, [UPOWER])
        self.OnBattery = False
        self.devs = dict()
        self.added()

    def added(self):
        DbusObject.added(self)
        self.enumerate()
        self.sigadd = self.obj.connect_to_signal("DeviceAdded", self.dev_added)
        self.sigdel = self.obj.connect_to_signal("DeviceRemoved", self.dev_removed)

    def update(self):
        DbusObject.update(self)
        was_init = self.init
        was_onbat = self.OnBattery
        self.update_prop(UPOWER, "OnBattery", bool)
        is_onbat = self.OnBattery
        if was_init:
            if was_onbat != is_onbat:
                if is_onbat:
                    self.notify("Now on battery power",
                                urgency=notify.URGENCY_NORMAL, timeout=2000)
                else:
                    self.notify("Now on external power",
                                urgency=notify.URGENCY_NORMAL, timeout=2000)
        self.init = True

    def removed(self):
        self.sigadd.remove()
        self.sigadd = None
        self.sigdel.remove()
        self.sigdel = None
        DbusObject.removed(self)

    def enumerate(self):
        devs = self.obj.EnumerateDevices(dbus_interface=UPOWER)
        for dev in devs:
            self.dev_added(dev)

    def dev_added(self, path):
        name = str(path)
        if not name in self.devs:
            self.devs[name] = PowerDevice(path)
            self.devs[name].added()

    def dev_removed(self, path):
        name = str(path)
        if name in self.devs:
            self.devs[name].removed()
            del self.devs[name]
