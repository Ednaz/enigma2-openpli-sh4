from Tools.Directories import SCOPE_SKIN, resolveFilename

hw_info = None

class HardwareInfo:
	device_name = _("unavailable")
	device_model = None
	device_version = ""
	device_revision = ""
	device_hdmi = True

	def __init__(self):
		global hw_info
		if hw_info:
			return
		hw_info = self

		print "[HardwareInfo] Scanning hardware info"
		# Version
		# Disable on spark because there is only a /proc/stb/info/model
		#try:
			#self.device_version = open("/proc/stb/info/version").read().strip()
		#except:
			#pass

		# Revision
		# Disable on spark because there is only a /proc/stb/info/model
		#try:
			#self.device_revision = open("/proc/stb/info/board_revision").read().strip()
		#except:
			#pass

		# Name ... bit odd, but history prevails
		try:
			self.device_name = open("/proc/stb/info/model").read().strip()
		except:
			pass

		# Model
		# Disable on spark because there is only a /proc/stb/info/model
		#for line in open((resolveFilename(SCOPE_SKIN, 'hw_info/hw_info.cfg')), 'r'):
			#if not line.startswith('#') and not line.isspace():
				#l = line.strip().replace('\t', ' ')
				#if ' ' in l:
					#infoFname, prefix = l.split()
				#else:
					#infoFname = l
					#prefix = ""
				#try:
					#self.device_model = prefix + open("/proc/stb/info/" + infoFname).read().strip()
					#break
				#except:
					#pass

		self.device_model = self.device_model or self.device_name

		# unify Xtrend device models
		if self.device_model in ("et9000", "et9100", "et9200", "et9500"):
			self.device_model = "et9x00"
		elif self.device_model in ("et6000", "et6x00"):
			self.device_model = "et6x00"
		elif self.device_model in ("et5000", "et5x00"):
			self.device_model = "et5x00"
		elif self.device_model in ("et4000", "et4x00"):
			self.device_model = "et4x00"

		# only some early DMM boxes do not have HDMI hardware
		# Disable on spark
		#self.device_hdmi =  self.device_model not in ("dm7025", "dm800", "dm8000")

		print "Detected: " + self.get_device_string()

	def get_device_name(self):
		return hw_info.device_name

	def get_device_model(self):
		return hw_info.device_model

	def get_device_version(self):
		return hw_info.device_version

	def get_device_revision(self):
		return hw_info.device_revision

	def get_device_string(self):
		if hw_info.device_revision:
			return "%s (%s-%s)" % (hw_info.device_model, hw_info.device_revision, hw_info.device_version)
		elif hw_info.device_version:
			return "%s (%s)" % (hw_info.device_model, hw_info.device_version)
		return hw_info.device_model

	def has_hdmi(self):
		return hw_info.device_hdmi
