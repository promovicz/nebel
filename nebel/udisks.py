from __future__ import absolute_import

import logging

from nebel.dbus import *

LOG = logging.getLogger("nebel.udisks")

DBUS_PROPERTIES = "org.freedesktop.DBus.Properties"

UDISKS = "org.freedesktop.UDisks2"
UDISKS_BLOCK = "org.freedesktop.UDisks2.Block"
UDISKS_DRIVE = "org.freedesktop.UDisks2.Drive"
UDISKS_ENCRYPTED = "org.freedesktop.UDisks2.Encrypted"
UDISKS_FILESYSTEM = "org.freedesktop.UDisks2.Filesystem"
UDISKS_JOB = "org.freedesktop.UDisks2.Job"
UDISKS_PARTITION = "org.freedesktop.UDisks2.Partition"
UDISKS_PARTITION_TABLE = "org.freedesktop.UDisks2.PartitionTable"

UDISKS_PATH = "/org/freedesktop/UDisks2"
UDISKS_PATH_DEVICES = UDISKS_PATH + "/block_devices"
UDISKS_PATH_DRIVES = UDISKS_PATH + "/drives"

OPERATION_FS_MOUNT = "filesystem-mount"
OPERATION_FS_UNMOUNT = "filesystem-unmount"

class DiskDrive(DbusPropsObject):
    def __init__(self, monitor, path):
        DbusPropsObject.__init__(self, UDISKS, path, [DBUS_PROPERTIES, UDISKS_DRIVE], log = LOG)
        self.monitor = monitor
        self.devices = dict()
        self.Ejectable = False
        self.Removable = False
        self.Media = None
        self.MediaAvailable = False
        self.MediaRemovable = False

    def ifs_added(self, ifprops):
        pass

    def ifs_removed(self, difprops):
        pass

    def added(self):
        DbusPropsObject.added(self)
        self.notify_added()

    def removed(self):
        DbusPropsObject.removed(self)
        self.notify_removed()

    def device_added(self, device):
        self.log.debug("drive %s: device added %s" % (self.path, device.path))
        self.devices[device.path] = device
        self.device_update(device)

    def device_update(self, device):
        self.log.debug("drive %s: device update %s" % (self.path, device.path))
        self.notify_changed()

    def device_removed(self, device):
        self.log.debug("drive %s: device removed %s" % (self.path, device.path))
        if device.path in self.devices:
            del self.devices[device.path]
            self.notify_changed()

    def notify_added(self):
        self.notify("Drive added")
    def notify_changed(self):
        self.notify("Drive changed")
    def notify_removed(self):
        self.notify("Drive removed")

    def notify(self, summary):
        if not (self.Ejectable or self.Removable or self.MediaRemovable):
            return
        message = "\nDrive  %s %s" % (self.Vendor.strip(), self.Model.strip())
        if self.MediaRemovable:
            if self.MediaAvailable:
                if self.Media:
                    message = message + ("\nMedium %s" % self.Media)
            else:
                message = message + "\nMedium none"
        if self.devices:
            message = message + "\n"
            for dev in self.devices.values():
                message = message + ("Device %s:\n" % dev.Device)
                if dev.is_encrypted:
                    message = message + ("  encrypted\n")
                if dev.is_filesystem:
                    message = message + ("  filesystem\n")
                if dev.is_partition:
                    message = message + ("  partition\n")
                if dev.is_ptable:
                    message = message + ("  partitioned\n")

        self.renotify("drive-%s" % self.path, summary, message=message, timeout=5000)

    def update(self):
        DbusPropsObject.update(self)
        was_init = self.init
        was_media  = self.Media
        was_mavail = self.MediaAvailable
        self.update_prop(UDISKS_DRIVE, "ConnectionBus", str)
        self.update_prop(UDISKS_DRIVE, "Seat", str)
        self.update_prop(UDISKS_DRIVE, "Vendor", str)
        self.update_prop(UDISKS_DRIVE, "Model", str)
        self.update_prop(UDISKS_DRIVE, "Serial", str)
        self.update_prop(UDISKS_DRIVE, "Removable", bool)
        self.update_prop(UDISKS_DRIVE, "Ejectable", bool)
        self.update_prop(UDISKS_DRIVE, "Media", str)
        self.update_prop(UDISKS_DRIVE, "MediaAvailable", bool)
        self.update_prop(UDISKS_DRIVE, "MediaRemovable", bool)
        self.update_prop(UDISKS_DRIVE, "Size", int)
        self.init = True
        if was_init:
            if was_media != self.Media or was_mavail != self.MediaAvailable:
                if self.MediaAvailable:
                    self.notify("Medium changed")
                else:
                    self.notify("Medium removed")

class DiskDevice(DbusPropsObject):
    def __init__(self, monitor, path):
        DbusPropsObject.__init__(self, UDISKS, path, [DBUS_PROPERTIES, UDISKS_BLOCK], log = LOG)
        self.drive = None
        self.monitor = monitor
        self.is_block = False
        self.is_encrypted = False
        self.is_filesystem = False
        self.is_partition = False
        self.is_ptable = False
        self.Drive = None
        self.Device = None

    def ifs_added(self, ifprops):
        ifs = map(str, ifprops.keys())
        if UDISKS_BLOCK in ifs:
            self.is_block = True
        if UDISKS_ENCRYPTED in ifs:
            self.is_encrypted = True
        if UDISKS_FILESYSTEM in ifs:
            self.is_filesystem = True
        if UDISKS_PARTITION in ifs:
            self.is_partition = True
        if UDISKS_PARTITION_TABLE in ifs:
            self.is_ptable = True
        self.update()

    def ifs_removed(self, difprops):
        pass

    def removed(self):
        DbusPropsObject.removed(self)
        if self.drive:
            self.drive.device_removed(self)
            self.drive = None

    def update(self):
        DbusPropsObject.update(self)
        was_init = self.init
        if self.is_block:
            self.update_prop(UDISKS_BLOCK, "Device", str)
            self.update_prop(UDISKS_BLOCK, "Drive", str)
            self.update_prop(UDISKS_BLOCK, "ReadOnly", str)
            self.update_prop(UDISKS_BLOCK, "IdLabel", str)
            self.update_prop(UDISKS_BLOCK, "IdType", str)
            self.update_prop(UDISKS_BLOCK, "IdUsage", str)
            self.update_prop(UDISKS_BLOCK, "IdVersion", str)
        if self.is_ptable:
            self.update_prop(UDISKS_PARTITION_TABLE, "Type", str)
            self.TableType = self.Type

        self.Type = None

        self.init = True
        # try to find the drive
        if not self.drive:
            if self.Drive and self.Drive in self.monitor.drives:
                self.drive = self.monitor.drives[self.Drive]
                self.drive.device_added(self)
        # and call it with updates
        if self.drive:
            self.drive.device_update(self)

class DiskJob(DbusObject):
    def __init__(self, monitor, path):
        DbusObject.__init__(self, UDISKS, path, [DBUS_PROPERTIES, UDISKS_JOB], log = LOG)
        self.monitor = monitor

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

class DiskMonitor(DbusObjectManager):
    def __init__(self):
        DbusObjectManager.__init__(self, UDISKS, UDISKS_PATH, [UDISKS], log = LOG)
        self.devices = dict()
        self.drives = dict()
        self.jobs = dict()
        self.added()

    def obj_instantiate(self, path, ifprops):
        ifs = map(str, ifprops.keys())
        name = str(path)
        objnew = False
        object = None
        if UDISKS_JOB in ifs:
            if not name in self.jobs:
                objnew = True
                self.jobs[name] = DiskJob(self, path)
            object = self.jobs[name]
        if (UDISKS_BLOCK in ifs
            or UDISKS_FILESYSTEM in ifs
            or UDISKS_PARTITION in ifs
            or UDISKS_PARTITION_TABLE in ifs):
            if not name in self.devices:
                objnew = True
                self.devices[name] = DiskDevice(self, path)
            object = self.devices[name]
        if UDISKS_DRIVE in ifs:
            if not name in self.drives:
                objnew = True
                self.drives[name] = DiskDrive(self, path)
            object = self.drives[name]
            # force drive detect
            for device in self.devices.values():
                device.update()
        if object == None:
            self.log.warning("unclassified object %s ifaces %s" % (name, ifs))
        return object

    def obj_destroy(self, obj, difs):
        ifs = map(str, difs)
        name = str(obj.path)
        object = None
        if UDISKS_JOB in ifs:
            if name in self.jobs:
                object = self.jobs[name]
                del self.jobs[name]
        if UDISKS_BLOCK in ifs:
            if name in self.devices:
                object = self.devices[name]
                del self.devices[name]
        if UDISKS_DRIVE in ifs:
            if name in self.drives:
                object = self.drives[name]
                del self.drives[name]
