import glib
import notify2 as notify
import nebel.udev
import nebel.upower
import nebel.urfkill

main = glib.MainLoop()

notify.init("nebel")

udev = nebel.udev.UDevMonitor()
power = nebel.upower.PowerMonitor()
rfkill = nebel.urfkill.RfkillMonitor()

main.run()
