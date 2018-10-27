from Wizard import wizardManager
from Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Tools.HardwareInfo import HardwareInfo
try:
	from Plugins.SystemPlugins.OSDPositionSetup.overscanwizard import OverscanWizard
except:
	OverscanWizard = None

from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.config import config, ConfigBoolean, configfile
from LanguageSelection import LanguageWizard
from enigma import eConsoleAppContainer, eTimer

import os

config.misc.firstrun = ConfigBoolean(default = True)
config.misc.languageselected = ConfigBoolean(default = True)
config.misc.do_overscanwizard = ConfigBoolean(default = OverscanWizard and config.skin.primary_skin.value == "PLi-FullNightHD/skin.xml")

class StartWizard(WizardLanguage, Rc):
	def __init__(self, session, silent = True, showSteps = False, neededTag = None):
		self.xmlfile = ["startwizard.xml"]
		WizardLanguage.__init__(self, session, showSteps = False)
		Rc.__init__(self)
		self["wizard"] = Pixmap()

	def markDone(self):
		# setup remote control, all stb have same settings except dm8000 which uses a different settings
		if HardwareInfo().get_device_name() == 'dm8000':
			config.misc.rcused.value = 0
		else:
			config.misc.rcused.value = 1
		config.misc.rcused.save()

		config.misc.firstrun.value = 0
		config.misc.firstrun.save()
		configfile.save()

def checkForAvailableAutoBackup():
	for dir in [name for name in os.listdir("/media/") if os.path.isdir(os.path.join("/media/", name))]:
		if os.path.isfile("/media/%s/backup/PLi-AutoBackup.tar.gz" % dir):
			return True
	return False

class AutoRestoreWizard(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Do you want to autorestore settings?"), type=MessageBox.TYPE_YESNO, timeout=20, default=True, simple=True)

	def close(self, value):
		if value:
			MessageBox.close(self, 43)
		else:
			MessageBox.close(self)

class AutoInstallWizard(Screen):
	skin = """<screen name="AutoInstall" position="fill" flags="wfNoBorder">
		<panel position="left" size="5%,*"/>
		<panel position="right" size="5%,*"/>
		<panel position="top" size="*,5%"/>
		<panel position="bottom" size="*,5%"/>
		<widget name="header" position="top" size="*,50" font="Regular;40"/>
		<widget name="progress" position="top" size="*,24" backgroundColor="#00242424"/>
		<widget name="AboutScrollLabel" font="Fixed;20" position="fill"/>
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self["progress"] = ProgressBar()
		self["progress"].setRange((0, 100))
		self["progress"].setValue(0)
		self["AboutScrollLabel"] = ScrollLabel("", showscrollbar=False)
		self["header"] = Label(_("Autoinstalling please wait for packages being updated"))

		self.logfile = open('/home/root/autoinstall.log', 'w')
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.appClosed)
		self.container.dataAvail.append(self.dataAvail)
		self.counter = 0

		import glob
		autoinstallfiles = glob.glob('/media/*/backup/autoinstall%s' % open('/sys/class/net/eth0/address', 'r').readline().strip().replace(":", ""))
		autoinstallfiles.sort(key=os.path.getmtime, reverse=True)
		for autoinstallfile in autoinstallfiles:
			self.packages = [x.strip() for x in open(autoinstallfile).readlines()]
			if self.packages:
				self.totalpackages = len(self.packages)
				# make sure we have a valid package list before attempting to restore packages
				self.container.execute("opkg update")
				return
		self.abort()

	def run_console(self):
		self.counter += 1
		self["progress"].setValue(100 * self.counter/self.totalpackages)
		self.package = self.packages.pop(0)
		self["header"].setText(_("Autoinstalling %s") % self.package)
		if self.package in [line.strip().split(":", 1)[1].strip() for line in open('/var/lib/opkg/status').readlines() if line.startswith('Package:')]:
			self.dataAvail('skip already installed package %s\n' % self.package)
			self.appClosed()
		else:
			try:
				if self.container.execute('opkg install %s' % self.package):
					raise Exception, "failed to execute command!"
					self.appClosed(True)
			except Exception, e:
				self.appClosed(True)

	def dataAvail(self, data):
		self["AboutScrollLabel"].appendText(data)
		self.logfile.write(data)

	def appClosed(self, retval=False):
		if retval:
			self.dataAvail("An error occurred during installing %s - Please try again later\n" % self.package)
		if self.packages:
			self.run_console()
		else:
			self["header"].setText(_("Autoinstalling Completed"))
			self.delay = eTimer()
			self.delay.callback.append(self.abort)
			self.delay.startLongTimer(5)

	def abort(self):
		self.container.appClosed.remove(self.appClosed)
		self.container.dataAvail.remove(self.dataAvail)
		self.container = None
		self.logfile.close()
		os.remove("/etc/.doAutoinstall")
		self.close(3)

if not os.path.isfile("/etc/installed"):
	from Components.Console import Console
	Console().ePopen("opkg list_installed | cut -d ' ' -f 1 > /etc/installed;chmod 444 /etc/installed")

wizardManager.registerWizard(AutoInstallWizard, os.path.isfile("/etc/.doAutoinstall"), priority=-10)
wizardManager.registerWizard(AutoRestoreWizard, config.misc.languageselected.value and config.misc.firstrun.value and checkForAvailableAutoBackup(), priority=-10)
wizardManager.registerWizard(LanguageWizard, config.misc.languageselected.value, priority=5)
if OverscanWizard:
	wizardManager.registerWizard(OverscanWizard, config.misc.do_overscanwizard.value, priority=10)
wizardManager.registerWizard(StartWizard, config.misc.firstrun.value, priority=20)
