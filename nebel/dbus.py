from __future__ import absolute_import

import logging

import dbus
import dbus.mainloop.glib

import notify2 as notify

LOG = logging.getLogger("nebel.dbus")

DBUS_PROPERTIES = "org.freedesktop.DBus.Properties"
DBUS_OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"

mainloop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
sysbus = dbus.SystemBus()

class DbusObject:
    def __init__(self, dest, path, ifaces, log=None):
        if log != None:
            self.log = log
        else:
            self.log = LOG
        self.dest = dest
        self.path = path
        self.ifaces = ifaces
        self.init = False
        self.obj = sysbus.get_object(dest, path)
        self.props = dbus.Interface(self.obj, DBUS_PROPERTIES)
        self.notifs = dict()
        self.sigpchg = None

    def get_interface(self, iface):
        return dbus.Interface(self.obj, iface)

    def added(self):
        self.log.info("added %s" % self.path)
        self.update()

    def removed(self):
        self.log.info("removed %s" % self.path)

    def update(self):
        self.log.debug("update %s" % self.path)

    def update_prop(self, iface, name, conv):
        raw = self.props.Get(iface, name)
        new = conv(raw)
        setattr(self, name, new)
        self.log.debug("%s: property %s.%s = %s" % (str(self.path), iface, name, new))

    def renotify(self, name, summary, timeout=1000, urgency=notify.URGENCY_LOW):
        self.log.info("renotify %s urgency %s timeout %s summary \"%s\"" % (name, urgency, timeout, summary))
        if name in self.notifs:
            n = self.notifs[name]
            n.update(summary)
        else:
            n = notify.Notification(summary)
            self.notifs[name] = n
        n.set_timeout(timeout)
        n.set_urgency(urgency)
        n.show()
        return n

    def recancel(self, name):
        self.log.info("recancel %s")
        n = None
        if name in self.notifs:
            n = self.notifs[name]
            n.cancel()
            del self.notifs[name]
        return n

class DbusPropsObject(DbusObject):

    def __init__(self, dest, path, ifaces, log=None):
        DbusObject.__init__(self, dest, path, ifaces, log = log)

    def added(self):
        DbusObject.added(self)
        self.connect_props_changed()

    def removed(self):
        self.disconnect_props_changed()
        DbusObject.removed(self)

    def connect_props_changed(self):
        self.sigpchg = self.obj.connect_to_signal("PropertiesChanged", self.props_changed)

    def disconnect_props_changed(self):
        if self.sigpchg != None:
            self.sigpchg.remove()
            self.sigpchg = None

    def props_changed(self, interface, changed, invalidated):
        self.log.debug("props changed %s interface %r (changed %r, invalidated %r)"
                       % (self.path, interface, changed, invalidated))
        for iface in self.ifaces:
            if interface == iface:
                self.update()
