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
        self.log.debug("updating %s" % self.path)

    def update_prop(self, iface, name, conv):
        raw = self.props.Get(iface, name, byte_arrays=True)
        new = conv(raw)
        if conv == str:
            new = new.rstrip('\0')
        setattr(self, name, new)
        self.log.debug("property %s.%s = %s" % (iface, name, new))

    def renotify(self, name, summary, message='', timeout=1000, urgency=notify.URGENCY_LOW):
        self.log.info("renotify %s urgency %s timeout %s summary \"%s\" message \"%s\"" % (name, urgency, timeout, summary, message))
        if name in self.notifs:
            n = self.notifs[name]
            n.update(summary, message)
        else:
            n = notify.Notification(summary, message)
            self.notifs[name] = n
        n.set_timeout(timeout)
        n.set_urgency(urgency)
        n.show()
        return n

    def recancel(self, name):
        self.log.info("recancel %s" % name)
        n = None
        if name in self.notifs:
            n = self.notifs[name]
            n.close()
            del self.notifs[name]
        return n

class DbusObjectManager(DbusObject):

    def __init__(self, dest, path, ifaces, log=None):
        DbusObject.__init__(self, dest, path, ifaces, log)
        self.objman = dbus.Interface(self.obj, DBUS_OBJECT_MANAGER)
        self.objs = dict()

    def added(self):
        DbusObject.added(self)
        self.connect_ifs()
        self.enumerate()

    def removed(self):
        DbusObject.removed(self)
        self.disconnect_ifs()

    def enumerate(self):
        objs = self.objman.GetManagedObjects()
        for obj in objs:
            self.ifs_added(obj, objs[obj])

    def ifs_added(self, path, ifprops):
        self.log.debug("ifaces added %s: %r" % (path, ifprops))
        obj = None
        new = False
        if not path in self.objs:
            new = True
            obj = self.obj_instantiate(path, ifprops)
            if obj != None:
                self.objs[path] = obj
        else:
            obj = self.objs[path]
        if obj != None:
            if new:
                obj.added()
            obj.ifs_added(ifprops)

    def ifs_removed(self, path, difs):
        self.log.debug("ifaces removed %s: %r" % (path, difs))
        obj = None
        if path in self.objs:
            obj = self.objs[path]
            del self.objs[path]
            self.obj_destroy(obj, difs)
            # XXX strictly incorrect
            obj.removed()

    def obj_instantiate(self, path, ifprops):
        return None

    def obj_destroy(self, obj, difs):
        pass

    def connect_ifs(self):
        self.sigadd = self.objman.connect_to_signal("InterfacesAdded", self.ifs_added)
        self.sigdel = self.objman.connect_to_signal("InterfacesRemoved", self.ifs_removed)

    def disconnect_ifs(self):
        if self.sigadd != None:
            self.sigadd.remove()
            self.sigadd = None
        if self.sigdel != None:
            self.sigdel.remove()
            self.sigdel = None

class DbusPropsObject(DbusObject):

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
        self.log.debug("props changed %s: %r (changed %r, invalidated %r)"
                       % (self.path, interface, changed, invalidated))
        for iface in self.ifaces:
            if interface == iface:
                self.update()
