from __future__ import absolute_import

import logging

import pyudev
import pyudev.glib

LOG = logging.getLogger("nebel.udev")

class UDevDevice:
    def __init__(self, path):
        self.path = path

    def added(self, device):
        LOG.info("dev add %s" % device.device_path)
        self.update(device)

    def update(self, device):
        LOG.info("dev upd %s type %s subsystem %s driver %s" %
                 (device.device_path, device.device_type,
                  device.subsystem, device.driver))

    def removed(self, device):
        LOG.info("dev rem %s" % device.device_path)

class UDevMonitor:
    def __init__(self):
        self.devs = dict()
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.observer = pyudev.glib.GUDevMonitorObserver(self.monitor)
        self.observer.connect('device-event', self.dev_event)
        self.monitor.start()

    def dev_event(self, observer, action, device):
        LOG.debug('event {0} on type {1} device {2}'
                  .format(device.action, device.device_type, device.device_path))
        path = device.device_path
        if action == 'add' or action == 'change':
            self.dev_add_change(path, device)
            return
        if action == 'remove':
            self.dev_remove(path, device)
            return

    def dev_add_change(self, path, device):
        if path in self.devs:
            dev = self.devs[path]
            dev.update(device)
        else:
            dev = UDevDevice(path)
            dev.added(device)
            self.devs[path] = dev

    def dev_remove(self, path, device):
        if path in self.devs:
            dev = self.devs[path]
            dev.removed(device)
            del self.devs[path]
