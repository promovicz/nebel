from __future__ import absolute_import

import math
import logging

import glib

from enum import Enum

from nebel.dbus import *

LOG = logging.getLogger("nebel.upower")

# polling interval for batteries
# ensures that we are a bit more timely than upower
BATTERY_POLL_INTERVAL = 30

UPOWER = "org.freedesktop.UPower"
UPOWER_DEVICE = "org.freedesktop.UPower.Device"

UPOWER_PATH = "/org/freedesktop/UPower"

# defines the next notification limit during charge
def charge_notify_limit(percent, seen):
    # notify every 10%
    return max((math.ceil((seen + 1) / 10.0) * 10) - 1, 0)

# defines the next notification limit during discharge
def discharge_notify_limit(percent, seen):
    if percent <= 25.0:
        # notify every 5%
        return min((math.floor((seen - 1) / 5.0) * 5) + 1, 100)
    else:
        # notify every 10%
        return min((math.floor((seen - 1) / 10.0) * 10) + 1, 100)

# defines notification urgency during discharge
def discharge_notify_urgency(percent):
    if percent <= 20.0:
        return notify.URGENCY_CRITICAL
    else:
        return notify.URGENCY_NORMAL

# defines notification timeout during discharge
def discharge_notify_timeout(percent):
    if percent <= 10:
        return 10000
    elif percent <= 20:
        return 5000
    else:
        return 2000

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

class PowerDevice(DbusPropsObject):
    def __init__(self, path):
        DbusPropsObject.__init__(self, UPOWER, path, [UPOWER_DEVICE], log = LOG)
        self.Type = DeviceType.unknown
        self.PowerSupply = False
        self.State = DeviceState.unknown
        self.Online = False
        self.TimeToEmpty = 0
        self.TimeToFull = 0
        self.Percentage = 0.0
        self.PercentageSeen = None

    def added(self):
        DbusPropsObject.added(self)
        if self.Type == DeviceType.battery:
            self.timer = glib.timeout_add(BATTERY_POLL_INTERVAL * 1000, self.tick)

    def removed(self):
        DbusPropsObject.removed(self)

    def tick(self):
        self.update()
        return True

    def update(self):
        DbusPropsObject.update(self)
        was_init = self.init
        was_state = self.State
        was_percent = self.Percentage
        was_timetoe = self.TimeToEmpty
        was_timetof = self.TimeToFull
        self.update_prop(UPOWER_DEVICE, "Type", DeviceType)
        self.update_prop(UPOWER_DEVICE, "PowerSupply", bool)
        self.update_prop(UPOWER_DEVICE, "State", DeviceState)
        self.update_prop(UPOWER_DEVICE, "Online", bool)
        self.update_prop(UPOWER_DEVICE, "TimeToEmpty", int)
        self.update_prop(UPOWER_DEVICE, "TimeToFull", int)
        self.update_prop(UPOWER_DEVICE, "Percentage", float)
        self.update_prop(UPOWER_DEVICE, "NativePath", str)
        is_state = self.State
        is_percent = self.Percentage

        if not was_init:
            if self.Type == DeviceType.battery:
                self.ChargeSeen = is_percent
                self.DischargeSeen = is_percent

        if was_init:
            if is_state != was_state:
                self.notify_state(is_state, was_state)

            if self.Type == DeviceType.battery:
                if is_state == DeviceState.charging:
                    self.notify_charge(is_percent)
                if is_state == DeviceState.discharging:
                    self.notify_discharge(is_percent)

        self.init = True

    def notify_state(self, new, old):
        LOG.info("%s: state now %s was %s" % (self.NativePath, new.name, old.name))
        if self.Type == DeviceType.battery:
            if new == DeviceState.charging:
                # initialize charge notification
                self.ChargeSeen = self.Percentage
            if new == DeviceState.discharging:
                # initialize discharge notification
                self.DischargeSeen = self.Percentage
            if old == DeviceState.charging and new == DeviceState.charged:
                # report full charge
                self.renotify("state", "%s is fully charged" % self.NativePath,
                              urgency=notify.URGENCY_NORMAL, timeout=5000)
            if new == DeviceState.empty:
                # report empty batteries
                self.renotify("%s is empty" % self.NativePath,
                              urgency=notify.URGENCY_NORMAL, timeout=5000)

    def notify_charge(self, percent):
        seen = self.ChargeSeen
        limit = charge_notify_limit(percent, seen)
        LOG.info("%s: charging: %s%% seen %s%% limit %s%%"
                 % (self.NativePath, percent, seen, limit))
        if percent > limit:
            self.renotify("progress", "%s now at %d%%" % (self.NativePath, percent),
                          urgency=notify.URGENCY_NORMAL, timeout=2000)
            self.ChargeSeen = percent

    def notify_discharge(self, percent):
        seen = self.DischargeSeen
        limit = discharge_notify_limit(percent, seen)
        LOG.info("%s: discharging: %s%% seen %s%% limit %s%%"
                 % (self.NativePath, percent, seen, limit))
        if percent < limit:
            urgency = discharge_notify_urgency(percent)
            timeout = discharge_notify_timeout(percent)
            self.renotify("progress", "%s now at %d%%" % (self.NativePath, percent),
                          urgency=urgency, timeout=timeout)
            self.DischargeSeen = percent


class PowerMonitor(DbusPropsObject):
    def __init__(self):
        DbusPropsObject.__init__(self, UPOWER, UPOWER_PATH, [UPOWER], log = LOG)
        self.batteries = list()
        self.OnBattery = False
        self.devs = dict()
        self.added()

    def added(self):
        DbusPropsObject.added(self)
        self.enumerate()
        self.sigadd = self.obj.connect_to_signal("DeviceAdded", self.dev_added)
        self.sigdel = self.obj.connect_to_signal("DeviceRemoved", self.dev_removed)

    def update(self):
        DbusPropsObject.update(self)
        was_init = self.init
        was_onbat = self.OnBattery
        self.update_prop(UPOWER, "OnBattery", bool)
        is_onbat = self.OnBattery
        if was_init:
            if was_onbat != is_onbat:
                if is_onbat:
                    self.renotify("on-battery", "Now on battery power",
                                  urgency=notify.URGENCY_NORMAL, timeout=2000)
                else:
                    self.renotify("on-battery", "Now on external power",
                                  urgency=notify.URGENCY_NORMAL, timeout=2000)
        self.init = True

    def removed(self):
        self.sigadd.remove()
        self.sigadd = None
        self.sigdel.remove()
        self.sigdel = None
        DbusPropsObject.removed(self)

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
