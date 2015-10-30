from __future__ import absolute_import

import dbus
import dbus.mainloop.glib
import notify2 as notify

DBUS_PROPERTIES = "org.freedesktop.DBus.Properties"

mainloop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
sysbus = dbus.SystemBus()

class DbusObject:
    def __init__(self, dest, path, ifaces):
        self.dest = dest
        self.path = path
        self.ifaces = ifaces
        self.init = False
        self.obj = sysbus.get_object(dest, path)
        self.props = dbus.Interface(self.obj, DBUS_PROPERTIES)

    def added(self):
        #print("%s: added" % self.path)
        self.update()
        self.sigpchg = self.obj.connect_to_signal("PropertiesChanged", self.props_changed)

    def removed(self):
        #print("%s: removed" % self.path)
        self.sigpchg.remove()
        self.sigpchg = None

    def update(self):
        pass
        #print("%s: update" % self.path)

    def props_changed(self, interface, changed, invalidated):
        #print("%s: props %r (changed %r, invalidated %r)"
        #      % (self.path, interface, changed, invalidated))
        for iface in self.ifaces:
            if interface == iface:
                self.update()

    def update_prop(self, iface, name, conv):
        raw = self.props.Get(iface, name)
        new = conv(raw)
        setattr(self, name, new)
        #print("%s: property %s.%s = %s" % (str(self.path), iface, name, new))

    def notify(self, message, timeout=1000, urgency=notify.URGENCY_LOW):
        n = notify.Notification(message)
        n.set_timeout(timeout)
        n.set_urgency(urgency)
        n.show()
