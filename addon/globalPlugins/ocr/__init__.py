"""NVDA OCR plugin
This plugin uses Tesseract for OCR: http://code.google.com/p/tesseract-ocr/
@author: James Teh <jamie@nvaccess.org>
@author: Rui Batista <ruiandrebatista@gmail.com>
@author: Alexey <aleks-samos@yandex.ru>
@copyright: 2011-2020 NV Access Limited, Rui Batista, alekssamos
@license: GNU General Public License version 2.0
"""

import sys
import os
import tempfile
import subprocess
from collections import namedtuple
from io import StringIO
from  threading import Timer
import configobj
from configobj import validate
import wx
import scriptHandler
import config
import globalPluginHandler
import gui
import api
from logHandler import log
import languageHandler
import addonHandler
addonHandler.initTranslation()
import textInfos.offsets
import ui
import locationHelper

PLUGIN_DIR = os.path.dirname(__file__)
TESSERACT_EXE = os.path.join(PLUGIN_DIR, "tesseract", "tesseract.exe")


IMAGE_RESIZE_FACTOR = 2


localesToTesseractLangs = {
"bg" : "bul",
"ca" : "cat",
"cs" : "ces",
"zh_CN" : "chi_tra",
"da" : "dan",
"de" : "deu",
"el" : "ell",
"en" : "eng",
"fi" : "fin",
"fr" : "fra",
"hu" : "hun",
"id" : "ind",
"it" : "ita",
"ja" : "jpn",
"ko" : "kor",
"lv" : "lav",
"lt" : "lit",
"nl" : "nld",
"nb_NO" : "nor",
"pl" : "pol",
"pt" : "por",
"ro" : "ron",
"ru" : "rus",
"sk" : "slk",
"sl" : "slv",
"es" : "spa",
"sr" : "srp",
"sv" : "swe",
"tg" : "tgl",
"tr" : "tur",
"uk" : "ukr",
"vi" : "vie"
}
tesseractLangsToLocales = {v : k for k, v in localesToTesseractLangs.items()}

def getAvailableTesseractLanguages():
	dataDir = os.path.join(os.path.dirname(__file__), "tesseract", "tessdata")
	dataFiles = [file for file in os.listdir(dataDir) if file.endswith('.traineddata')]
	return [os.path.splitext(file)[0] for file in dataFiles]

def getDefaultLanguage():
	lang = languageHandler.getLanguage()
	if lang not in localesToTesseractLangs and "_" in lang:
		lang = lang.split("_")[0]
	return localesToTesseractLangs.get(lang, "eng")

class SettingsDialog(gui.SettingsDialog):
	# Pop a dialog with available OCR languages to set
	title = _("OCR Settings")
	tlangs = getAvailableTesseractLanguages()
	
	def makeSettings(self, sizer):
		settingsSizerHelper = gui.guiHelper.BoxSizerHelper(self, sizer=sizer)

		langs = sorted(self.tlangs)
		choices = [languageHandler.getLanguageDescription(tesseractLangsToLocales[lang]) or
			tesseractLangsToLocales[lang] for lang in langs]
		log.debug("Available OCR languages: %s", ", ".join(choices))
		
		curlang = getConfig()['language']
		try:
			select = langs.index(curlang)
		except ValueError:
			select = langs.index('en')
		self.language = settingsSizerHelper.addLabeledControl(_("Select OCR Language"), wx.Choice, choices=choices)
		self.language.SetSelection(select)
		
		curlang2 = getConfig()['language2']
		try:
			select2 = langs.index(curlang2)
		except ValueError:
			select2 = langs.index('en')
		self.language2 = settingsSizerHelper.addLabeledControl(_("Select second OCR Language"), wx.Choice, choices=choices)
		self.language2.SetSelection(select2)
	
	def postInit(self):
		self.language.SetFocus()

	def onOk(self, event):
		getConfig()["language"] = self.tlangs[self.language.GetSelection()]
		getConfig()["language2"] = self.tlangs[self.language2.GetSelection()]

		try:
			getConfig().write()
		except IOError:
			log.error("Error writing ocr configuration", exc_info=True)
		super(SettingsDialog, self).onOk(event)

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super(globalPluginHandler.GlobalPlugin, self).__init__()
		self.ocrSettingsItem = gui.mainFrame.sysTrayIcon.preferencesMenu.Append(wx.ID_ANY,
			# Translators: The name of the OCR settings item
			# in the NVDA Preferences menu.
			_("OCR settings..."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, lambda evt: gui.mainFrame._popupSettingsDialog(SettingsDialog), self.ocrSettingsItem)

	def terminate(self):
		try:
			gui.mainFrame.sysTrayIcon.preferencesMenu.RemoveItem(self.ocrSettingsItem)
		except wx.PyDeadObjectError:
			pass

	def script_ocrNavigatorObject(self, gesture):
		nav = api.getNavigatorObject()
		left, top, width, height = nav.location
		bmp = wx.EmptyBitmap(width, height)
		# Tesseract copes better if we convert to black and white...
		## img = img.convert(mode='L')
		# and increase the size.
		## img = img.resize((width * IMAGE_RESIZE_FACTOR, height * IMAGE_RESIZE_FACTOR), Image.BICUBIC)
		mem = wx.MemoryDC(bmp)
		mem.Blit(0, 0, width, height, wx.ScreenDC(), left, top)
		
		baseFile = os.path.join(tempfile.gettempdir(), "nvda_ocr")
		try:
			imgFile = baseFile + ".png"
			txtFile = baseFile + ".txt"
			bmp.SaveFile(imgFile, wx.BITMAP_TYPE_PNG)
			
			ui.message(_("Running OCR"))
			lang = getConfig()['language']
			lang2 = getConfig()['language2']
			if not lang == lang2:
				mlangs = lang + "+" + lang2
			else:
				mlangs = lang
			# Hide the Tesseract window.
			si = subprocess.STARTUPINFO()
			si.dwFlags = subprocess.STARTF_USESHOWWINDOW
			si.wShowWindow = subprocess.SW_HIDE
			subprocess.check_call((TESSERACT_EXE, imgFile, baseFile, "-l", mlangs),
				startupinfo=si)
		finally:
			try:
				os.remove(imgFile)
			except OSError:
				pass
		# Let the user review the OCR output.
		result = ""
		try:
			with open(txtFile, encoding="UTF-8") as f: result = f.read().strip()
		except: pass
		os.remove(txtFile)
		if result != "":
			ui.message(_("Done"))
			try:
				ui.browseableMessage(result, _("OCR Result"))
			except:
				ui.message(result)
		else:
			ui.message(_("Error"))
	script_ocrNavigatorObject.__doc__ = _('Recognize text use tesseract.')
	__gestures = {
		"kb:NVDA+r": "ocrNavigatorObject",
	}


_config = None
configspec = StringIO("""
language=string(default={defaultLanguage})
language2=string(default={defaultLanguage})
""".format(defaultLanguage=getDefaultLanguage()))
def getConfig():
	global _config
	if not _config:
		path = os.path.join(config.getUserDefaultConfigPath(), "ocr.ini")
		_config = configobj.ConfigObj(path, configspec=configspec)
		val = validate.Validator()
		_config.validate(val)
	return _config