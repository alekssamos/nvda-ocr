"""Download and extract dependencies.
"""

import os
import re
import urllib
import fnmatch
import shutil
import zipfile
import tarfile

TESSERACT_DOWNLOAD_URL = "https://excellmedia.dl.sourceforge.net/project/tesseract-ocr-alt/tesseract-ocr-3.02-win32-portable.zip"
TESSERACT_LANGS_DOWNLOAD_URLS = {
	## add other languages
	## from https://sourceforge.net/projects/tesseract-ocr-alt/files/
	## eng default exist if not remove
	## "eng": "https://netix.dl.sourceforge.net/project/tesseract-ocr-alt/tesseract-ocr-3.02.eng.tar.gz",
	"rus": "https://netix.dl.sourceforge.net/project/tesseract-ocr-alt/tesseract-ocr-3.02.rus.tar.gz"
}

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
DEPS_DIR = os.path.join(ROOT_DIR, "deps")
PLUGIN_DIR = os.path.join(ROOT_DIR, "addon", "globalPlugins", "ocr")
TESSDATA_DIR = os.path.join(PLUGIN_DIR, "tesseract", "tessdata")

depFiles = set()

def downloadDeps():
	try:
		os.mkdir(DEPS_DIR)
	except OSError:
		pass

	urls = [TESSERACT_DOWNLOAD_URL]
	urls.extend(list(TESSERACT_LANGS_DOWNLOAD_URLS.values()))

	print("Downloading dependencies")
	for url in urls:
		fn = os.path.basename(url)
		localPath = os.path.join(DEPS_DIR, fn)
		depFiles.add(localPath)
		if os.path.isfile(localPath):
			print("%s already downloaded" % fn)
			continue
		print "Downloading %s" % fn
		# Download to a temporary path in case the download aborts.
		tempPath = localPath + ".tmp"
		urllib.urlretrieve(url, tempPath)
		os.rename(tempPath, localPath)

TESSERACT_FILES = ["tesseract.exe", "tessdata/*",
	"doc/AUTHORS", "doc/COPYING"]
def extractTesseract():
	for zfn in depFiles:
		if fnmatch.fnmatch(zfn, "*/tesseract-ocr-*-win32-portable.zip"):
			break
	else:
		assert False

	tessDir = os.path.join(PLUGIN_DIR, "tesseract")
	print "Extracting Tesseract"
	shutil.rmtree(tessDir, ignore_errors=True)
	with zipfile.ZipFile(zfn) as zf:
		for realFn in zf.namelist():
			if realFn.endswith("/"):
				continue
			# Strip the top level distribution directory.
			fn = realFn.split("/", 1)[1]
			extractFn = os.path.join(tessDir, fn.replace("/", os.path.sep))
			if not any(fnmatch.fnmatch(fn, pattern) for pattern in TESSERACT_FILES):
				continue
			try:
				os.makedirs(os.path.dirname(extractFn))
			except OSError:
				pass
			with zf.open(realFn) as inf, file(extractFn, "wb") as outf:
				shutil.copyfileobj(inf, outf)

def extractLangTesseract(lang):
	tmp1 = os.path.join(PLUGIN_DIR, "tesseract-ocr", "tessdata")
	for gzfn in depFiles:
		if fnmatch.fnmatch(gzfn, "*/tesseract-ocr-*.???.tar.gz"):
			break
	else:
		assert False
	print "Extracting {} Tesseract".format(lang)
	tf = tarfile.open(gzfn)
	for tfn in tf.getnames():
		tf.extract(tfn, path = PLUGIN_DIR)
	if not os.path.isdir(TESSDATA_DIR):
		os.makedirs(TESSDATA_DIR)
	folder = []
	for i in os.walk(tmp1):
		folder.append(i)
	for address, dirs, files in folder:
		for file in files:
			curpath =os.path.join(address, file)
			shutil.copy(curpath, os.path.join(TESSDATA_DIR, file))
			os.remove(curpath)
	shutil.rmtree(os.path.join(tmp1, ".."))

def main():
	downloadDeps()
	extractTesseract()
	for tl in TESSERACT_LANGS_DOWNLOAD_URLS:
		extractLangTesseract(tl)

if __name__ == "__main__":
	main()
