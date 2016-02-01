from __future__ import absolute_import

import logging

from nebel.dbus import *

LOG = logging.getLogger("nebel.udisks")

UDISKS = "org.freedesktop.UDisks2"
UDISKS_BLOCK = "org.freedesktop.UDisks2.Block"
UDISKS_DRIVE = "org.freedesktop.UDisks2.Drive"
UDISKS_JOB = "org.freedesktop.UDisks2.Job"

UDISKS_PATH = "/org/freedesktop/UDisks2"

OPERATION_FS_MOUNT = "filesystem-mount"
OPERATION_FS_UNMOUNT = "filesystem-unmount"

class DiskDevice(DbusPropsObject):
    def __init__(self, path):
        DbusPropsObject.__init__(self, UDISKS, path, [UDISKS_BLOCK], log = LOG)

    def ifs_added(self, ifprops):
        pass

    def ifs_removed(self, ifs):
        pass

class DiskJob(DbusObject):

    def __init__(self, path):
        DbusObject.__init__(self, UDISKS, path, [UDISKS_JOB], log = LOG)

    def ifs_added(self, difprops):
        ifprops = dict()
        for key in difprops.keys():
            ifprops[str(key)] = difprops[key]
        djob = ifprops[UDISKS_JOB]
        job = dict()
        for key in djob.keys():
            job[str(key)] = djob[key]
        self.Operation = str(job["Operation"])
        self.Cancelable = bool(job["Cancelable"])
        self.ProgressValid = bool(job["ProgressValid"])
        self.Progress = float(job["Progress"])
        self.Objects = job["Objects"]
        self.log.info("op %s objs %s" % (self.Operation, self.Objects))
        self.sigcompleted = self.obj.connect_to_signal("Completed", self.completed)
        if self.Operation == OPERATION_FS_MOUNT:
            bpath = self.Objects[0]
            self.renotify("mount-%s" % bpath, "Mounting %s..." % bpath, timeout=5000)
        if self.Operation == OPERATION_FS_UNMOUNT:
            bpath = self.Objects[0]
            self.renotify("unmount-%s" % bpath, "Unmounting %s" % bpath, timeout=5000)

    def ifs_removed(self, ifs):
        pass

    def update(self):
        pass

    def completed(self, success, message):
        self.log.info("%s: completed sucess %s message %s" % (self.path, success, message))
        if self.Operation == OPERATION_FS_MOUNT:
            bpath = self.Objects[0]
            self.renotify("mount-%s" % bpath, "Mounting %s...done." % bpath, timeout=1000)
        if self.Operation == OPERATION_FS_UNMOUNT:
            bpath = self.Objects[0]
            self.renotify("unmount-%s" % bpath, "Unmounting %s...done." % bpath, timeout=1000)

class DiskMonitor(DbusObject):

    def __init__(self):
        DbusObject.__init__(self, UDISKS, UDISKS_PATH, [UDISKS], log = LOG)
        self.devs = dict()
        self.jobs = dict()
        self.objman = self.get_interface(DBUS_OBJECT_MANAGER)
        self.added()

    def added(self):
        DbusObject.added(self)
        self.enumerate()
        self.sigadd = self.objman.connect_to_signal("InterfacesAdded", self.ifs_added)
        self.sigdel = self.objman.connect_to_signal("InterfacesRemoved", self.ifs_removed)

    def enumerate(self):
        pass

    def ifs_added(self, path, ifprops):
        ifs = map(str, ifprops.keys())
        name = str(path)
        objnew = False
        object = None
        if UDISKS_JOB in ifs:
            if not name in self.jobs:
                objnew = True
                self.jobs[name] = DiskJob(path)
            object = self.jobs[name]
        if UDISKS_BLOCK in ifs:
            if not name in self.devs:
                objnew = True
                self.devs[name] = DiskDevice(path)
            object = self.devs[name]
        if UDISKS_DRIVE in ifs:
            self.log.info("IS A DRIVE")
        if object != None and objnew:
            object.added()
            object.ifs_added(ifprops)

    def ifs_removed(self, path, difs):
        ifs = map(str, difs)
        name = str(path)
        object = None
        if UDISKS_JOB in ifs:
            if name in self.jobs:
                object = self.jobs[name]
                del self.jobs[name]
        if UDISKS_BLOCK in ifs:
            if name in self.devs:
                object = self.devs[name]
                del self.devs[name]
        if object != None:
            object.ifs_removed(ifs)
            object.removed()
