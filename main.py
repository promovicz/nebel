import logging
import glib
import notify2 as notify
import nebel.udev
import nebel.udisks
import nebel.upower
import nebel.urfkill

LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)-15s [%(name)-15s] %(message)s'
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

main = glib.MainLoop()

notify.init("nebel")

#udev = nebel.udev.UDevMonitor()
disks = nebel.udisks.DiskMonitor()
power = nebel.upower.PowerMonitor()
rfkill = nebel.urfkill.RfkillMonitor()

main.run()
