from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.config import config, configfile
from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Harddisk import getNonNetworkMediaMounts
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.SystemInfo import SystemInfo
from Tools.BoundFunction import boundFunction
from Tools.Downloader import downloadWithProgress
from Tools.HardwareInfo import HardwareInfo
from Tools.Multiboot import GetImagelist, GetCurrentImage, GetCurrentImageMode
import os, urllib2, json, time, zipfile
from enigma import eTimer, eEPGCache

def checkimagefiles(files):
	return len([x for x in files if 'kernel' in x and '.bin' in x or x in ('uImage', 'rootfs.bin', 'root_cfe_auto.bin', 'root_cfe_auto.jffs2', 'oe_rootfs.bin', 'e2jffs2.img', 'rootfs.tar.bz2')]) == 2

class SelectImage(Screen):
	def __init__(self, session, *args):
		Screen.__init__(self, session)
		self.skinName = "ChoiceBox"
		self.session = session
		self.jsonlist = None
		self.imagesList = None
		self.setIndex = 0
		self.expanded = []
		self.setTitle(_("Select Image"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["list"] = ChoiceList(list=[ChoiceEntryComponent('',((_("Retreiving image list - Please wait...")), "Waiter"))])

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"cancel": boundFunction(self.close, None),
			"red": boundFunction(self.close, None),
			"green": self.keyOk,
			"yellow": self.keyDelete,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"leftRepeated": self.keyLeft,
			"rightRepeated": self.keyRight,
			"menu": boundFunction(self.close, True),
		}, -1)

		self.delay = eTimer()
		self.delay.callback.append(self.getImagesList)
		self.delay.start(0, True)

	def getImagesList(self):

		def getImages(path, files):
			for file in [x for x in files if x.endswith('.zip') and model in x]:
				try:
					if checkimagefiles([x.split(os.sep)[-1] for x in zipfile.ZipFile(file).namelist()]):
						medium = path.split(os.sep)[-1]
						if medium not in self.imagesList:
							self.imagesList[medium] = {}
						self.imagesList[medium][file] = { 'link': file, 'name': file.split(os.sep)[-1]}
				except:
					pass

		model = HardwareInfo().get_device_model()

		if not self.imagesList:
			if not self.jsonlist:
				try:
					self.jsonlist = json.load(urllib2.urlopen('https://openpli.org/download/json/%s' % model))
				except:
					pass
			self.imagesList = dict(self.jsonlist) if self.jsonlist else {}

			for media in getNonNetworkMediaMounts():
				if not(SystemInfo['HasMMC'] and "/mmc" in media):
					getImages(media, ["%s/%s" % (media, x) for x in os.listdir(media) if x.endswith('.zip') and model in x])
					if "downloaded_images" in os.listdir(media):
						media = "%s/downloaded_images" % media
						if os.path.isdir(media) and not os.path.islink(media) and not os.path.ismount(media):
							getImages(media, ["%s/%s" % (media, x) for x in os.listdir(media) if x.endswith('.zip') and model in x])

		list = []
		for catagorie in reversed(sorted(self.imagesList.keys())):
			if catagorie in self.expanded:
				list.append(ChoiceEntryComponent('expanded',((str(catagorie)), "Expander")))
				for image in reversed(sorted(self.imagesList[catagorie].keys())):
					if not SystemInfo["canMultiBoot"] or image.endswith('_multiboot.zip'):
						list.append(ChoiceEntryComponent('verticalline',((str(self.imagesList[catagorie][image]['name'])), str(self.imagesList[catagorie][image]['link']))))
			else:
				for image in self.imagesList[catagorie].keys():
					if not SystemInfo["canMultiBoot"] or image.endswith('_multiboot.zip'):
						list.append(ChoiceEntryComponent('expandable',((str(catagorie)), "Expander")))
						break
		if list:
			self["list"].setList(list)
			if self.setIndex:
				self["list"].moveToIndex(self.setIndex if self.setIndex < len(list) else len(list) - 1)
				if self["list"].l.getCurrentSelection()[0][1] == "Expander":
					self.setIndex -= 1
					if self.setIndex:
						self["list"].moveToIndex(self.setIndex if self.setIndex < len(list) else len(list) - 1)
				self.setIndex = 0
			self.selectionChanged()
		else:
			self.session.openWithCallback(self.close, MessageBox, _("Cannot find images - please try later"), type=MessageBox.TYPE_ERROR, timeout=3)

	def keyOk(self):
		currentSelected = self["list"].l.getCurrentSelection()
		if currentSelected[0][1] == "Expander":
			if currentSelected[0][0] in self.expanded:
				self.expanded.remove(currentSelected[0][0])
			else:
				self.expanded.append(currentSelected[0][0])
			self.getImagesList()
		elif currentSelected[0][1] != "Waiter":
			self.session.openWithCallback(self.getImagesList, FlashImage, currentSelected[0][0], currentSelected[0][1])

	def keyDelete(self):
		currentSelected= self["list"].l.getCurrentSelection()[0][1]
		if not("://" in currentSelected or currentSelected in ["Expander", "Waiter"]):
			os.remove(currentSelected)
			currentSelected = ".".join([currentSelected[:-4], "unzipped"])
			if os.path.isdir(currentSelected):
				import shutil
				shutil.rmtree(currentSelected)
			self.setIndex = self["list"].getSelectedIndex()
			self.imagesList = []
			self["list"].setList([ChoiceEntryComponent('',((_("Refreshing image list - Please wait...")), "Waiter"))])
			self.delay.start(0, True)

	def selectionChanged(self):
		currentSelected = self["list"].l.getCurrentSelection()
		if "://" in currentSelected[0][1] or currentSelected[0][1] in ["Expander", "Waiter"]:
			self["key_yellow"].setText("")
		else:
			self["key_yellow"].setText(_("Delete image"))
		if currentSelected[0][1] == "Waiter":
			self["key_green"].setText("")
		else:
			self["key_green"].setText((_("Compress") if currentSelected[0][0] in self.expanded else _("Expand")) if currentSelected[0][1] == "Expander" else _("Flash Image"))

	def keyLeft(self):
		self["list"].instance.moveSelection(self["list"].instance.pageUp)
		self.selectionChanged()

	def keyRight(self):
		self["list"].instance.moveSelection(self["list"].instance.pageDown)
		self.selectionChanged()

	def keyUp(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		self.selectionChanged()

	def keyDown(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)
		self.selectionChanged()

class FlashImage(Screen):
	skin = """<screen position="center,center" size="640,150" flags="wfNoBorder" backgroundColor="#54242424">
		<widget name="header" position="5,10" size="e-10,50" font="Regular;40" backgroundColor="#54242424"/>
		<widget name="info" position="5,60" size="e-10,130" font="Regular;24" backgroundColor="#54242424"/>
		<widget name="progress" position="5,e-39" size="e-10,24" backgroundColor="#54242424"/>
	</screen>"""
	
	def __init__(self, session,  imagename, source):
		Screen.__init__(self, session)
		self.containerbackup = None
		self.containerofgwrite = None
		self.getImageList = None
		self.downloader = None
		self.source = source
		self.imagename = imagename

		self["header"] = Label(_("Backup settings"))
		self["info"] = Label(_("Save settings and EPG data"))
		self["progress"] = ProgressBar()
		self["progress"].setRange((0, 100))
		self["progress"].setValue(0)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"cancel": self.abort,
			"red": self.abort,
		}, -1)

		self.delay = eTimer()
		self.delay.callback.append(self.confirmation)
		self.delay.start(0, True)
		self.hide()

	def confirmation(self):
		recordings = self.session.nav.getRecordings()
		if not recordings:
			next_rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
		if recordings or (next_rec_time > 0 and (next_rec_time - time.time()) < 360):
			self.message = _("Recording(s) are in progress or coming up in few seconds!\nDo you still want to flash image\n%s?") % self.imagename
		else:
			self.message = _("Do you want to flash image\n%s") % self.imagename
		if SystemInfo["canMultiBoot"]:
			self.getImageList = GetImagelist(self.getImagelistCallback)
		else:
			choices = [(_("Yes, with backup"), "with backup"), (_("No, do not flash image"), False), (_("Yes, without backup"), "without backup")]
			self.session.openWithCallback(self.backupsettings, MessageBox, self.message , list=choices, default=False, simple=True)

	def getImagelistCallback(self, imagedict):
		self.getImageList = None
		choices = []
		currentimageslot = GetCurrentImage()
		for x in range(1,5):
			if x in imagedict:
				choices.append(((_("slot%s - %s (current image) with, backup") if x == currentimageslot else _("slot%s - %s, with backup")) % (x, imagedict[x]['imagename']), (x, "with backup")))
			else:
				choices.append((_("slot%s - empty, with backup") % x, (x, "with backup")))
		choices.append((_("No, do not flash image"), False))
		for x in range(1,5):
			if x in imagedict:
				choices.append(((_("slot%s - %s (current image), without backup") if x == currentimageslot else _("slot%s - %s, without backup")) % (x, imagedict[x]['imagename']), (x, "without backup")))
			else:
				choices.append((_("slot%s - empty, without backup") % x, (x, "without backup")))
		self.session.openWithCallback(self.backupsettings, MessageBox, self.message, list=choices, default=currentimageslot, simple=True)

	def backupsettings(self, retval):

		if retval:

			if SystemInfo["canMultiBoot"]:
				self.multibootslot = retval[0]
				doBackup = retval[1] == "with backup"
			else:
				doBackup = retval == "with backup"

			BACKUP_SCRIPT = "/usr/lib/enigma2/python/Plugins/Extensions/AutoBackup/settings-backup.sh"

			def findmedia(destination):
				def avail(path):
					if not(SystemInfo["HasMMC"] and '/mmc' in path):
						statvfs = os.statvfs(path)
						return (statvfs.f_bavail * statvfs.f_frsize) / (1 << 20) >= 500 and path
				for path in [destination] + getNonNetworkMediaMounts():
					if avail(path):
						return path

			self.destination = findmedia(os.path.isfile(BACKUP_SCRIPT) and config.plugins.autobackup.where.value or "/media/hdd")

			if self.destination:

				destination = "/".join([self.destination, 'downloaded_images'])
				self.zippedimage = "://" in self.source and "/".join([destination, self.imagename]) or self.source
				self.unzippedimage = "/".join([destination, '%s.unzipped' % self.imagename[:-4]])
			
				if os.path.isfile(destination):
					os.remove(destination)
				if not os.path.isdir(destination):
					os.mkdir(destination)

				if doBackup:
					if os.path.isfile(BACKUP_SCRIPT):
						self["info"].setText(_("Backing up to: %s") % self.destination)
						configfile.save()
						if config.plugins.autobackup.epgcache.value:
							eEPGCache.getInstance().save()
						self.containerbackup = Console()
						self.containerbackup.ePopen("%s%s'%s' %s" % (BACKUP_SCRIPT, config.plugins.autobackup.autoinstall.value and " -a " or " ", self.destination, int(config.plugins.autobackup.prevbackup.value)), self.backupsettingsDone)
					else:
						self.session.openWithCallback(self.startDownload, MessageBox, _("Unable to backup settings as the AutoBackup plugin is missing, do you want to continue?"), default=False, simple=True)
				else:
					self.startDownload()
			else:
				self.session.openWithCallback(self.abort, MessageBox, _("Could not find suitable media - Please insert a media (e.g. USB stick) and try again!"), type=MessageBox.TYPE_ERROR, simple=True)
		else:
			self.abort()

	def backupsettingsDone(self, data, retval, extra_args):
		self.containerbackup = None
		if retval == 0:
			self.startDownload()
		else:	
			self.session.openWithCallback(self.abort, MessageBox, _("Error during backup settings\n%s") % reval, type=MessageBox.TYPE_ERROR, simple=True)
		
	def startDownload(self, reply=True):
		self.show()
		if reply:
			if "://" in self.source:
				from Tools.Downloader import downloadWithProgress
				self["header"].setText(_("Downloading Image"))
				self["info"].setText(self.imagename)
				self.downloader = downloadWithProgress(self.source, self.zippedimage)
				self.downloader.addProgress(self.downloadProgress)
				self.downloader.addEnd(self.downloadEnd)
				self.downloader.addError(self.downloadError)
				self.downloader.start()
			else:
				self.unzip()
		else:
			self.abort()

	def downloadProgress(self, current, total):
		self["progress"].setValue(int(100 * current / total))

	def downloadError(self, reason, status):
		self.downloader.stop()
		self.session.openWithCallback(self.abort, MessageBox, _("Error during downloading image\n%s\n%s") % (self.imagename, reason), type=MessageBox.TYPE_ERROR, simple=True)
		
	def downloadEnd(self):
		self.downloader.stop()
		self.unzip()
		
	def unzip(self):
		try:
			zipfile.ZipFile(self.zippedimage, 'r').extractall(self.unzippedimage)
			self.flashimage()	
		except:
			self.session.openWithCallback(self.abort, MessageBox, _("Error during unzipping image\n%s") % self.imagename, type=MessageBox.TYPE_ERROR, simple=True)

	def flashimage(self):
		def findimagefiles(path):
			for path, subdirs, files in os.walk(path):
				if not subdirs and files:
					return checkimagefiles(files) and path
		imagefiles = findimagefiles(self.unzippedimage)
		if imagefiles:
			if SystemInfo["canMultiBoot"]:
				command = "/usr/bin/ofgwrite -k -r -m%s '%s'" % (self.multibootslot, imagefiles)
			else:
				command = "/usr/bin/ofgwrite -k -r '%s'" % imagefiles
			self.containerofgwrite = Console()
			self.containerofgwrite.ePopen(command, self.FlashimageDone)
		else:
			self.session.openWithCallback(self.abort, MessageBox, _("Image to install is invalid\n%s") % self.imagename, type=MessageBox.TYPE_ERROR, simple=True)

	def FlashimageDone(self, data, retval, extra_args):
		self.containerofgwrite = None
		if retval == 0:
			self["header"].setText(_("Flashing image succesfull"))
			self["info"].setText(_("%s\nPress exit to close") % self.imagename)
			self["progress"].hide()
		else:
			self.session.openWithCallback(self.abort, MessageBox, _("Flashing image was not succesfull\n%s") % self.imagename, type=MessageBox.TYPE_ERROR, simple=True)

	def abort(self, reply=None):
		if self.getImageList or self.containerofgwrite:
			return 0
		if self.downloader:
			self.downloader.stop()
		if self.containerbackup:
			self.containerbackup.killAll()
		self.close()

class MultibootSelection(SelectImage):
	def __init__(self, session, *args):
		Screen.__init__(self, session)
		self.skinName = "ChoiceBox"
		self.session = session
		self.imagesList = None
		self.expanded = []
		self.setTitle(_("Select Multiboot"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Reboot"))
		self["list"] = ChoiceList(list=[ChoiceEntryComponent('',((_("Retreiving image slots - Please wait...")), "Waiter"))])

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"cancel": boundFunction(self.close, None),
			"red": boundFunction(self.close, None),
			"green": self.keyOk,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"leftRepeated": self.keyLeft,
			"rightRepeated": self.keyRight,
			"menu": boundFunction(self.close, True),
		}, -1)

		self.delay = eTimer()
		self.delay.callback.append(self.getImagesList)
		self.delay.start(0, True)

	def getImagesList(self, reply=None):
		self.getImageList = GetImagelist(self.getImagelistCallback)

	def getImagelistCallback(self, imagesdict):
		list = []
		currentimageslot = GetCurrentImage()
		mode = SystemInfo["canMode12"] and GetCurrentImageMode() or 0
		for x in sorted(imagesdict.keys()):
			list.append(ChoiceEntryComponent('',((_("slot%s - %s mode 1 (current image)") if x == currentimageslot and mode == 1 else _("slot%s - %s mode 1")) % (x, imagesdict[x]['imagename']), x)))
			if SystemInfo["canMode12"]:
				list.append(ChoiceEntryComponent('',((_("slot%s - %s mode 12 (current image)") if x == currentimageslot and mode == 12 else _("slot%s - %s mode 12")) % (x, imagesdict[x]['imagename']), x + 12)))
		self["list"].setList(list)

	def keyOk(self):
		currentSelected = self["list"].l.getCurrentSelection()
		slot = currentSelected[0][1]
		if currentSelected[0][1] != "Waiter":
			model = HardwareInfo().get_device_model()
			if slot < 12:
				startupFileContents = "boot emmcflash0.kernel%s 'root=/dev/mmcblk0p%s rw rootwait %s_4.boxmode=1'\n" % (slot, slot * 2 + 1, model)
			else:
				slot -= 12
				startupFileContents = "boot emmcflash0.kernel%s 'brcm_cma=520M@248M brcm_cma=%s@768M root=/dev/mmcblk0p%s rw rootwait %s_4.boxmode=12'\n" % (slot, SystemInfo["canMode12"], slot * 2 + 1, model)
			for media in ['/media/%s' % x for x in os.listdir('/media') if x.startswith('mmc')]:
				if 'STARTUP' in os.listdir(media):
					open('%s/%s' % (media, 'STARTUP'), 'w').write(startupFileContents)
					break
			from Screens.Standby import TryQuitMainloop
			self.session.open(TryQuitMainloop, 2)

	def selectionChanged(self):
		pass
