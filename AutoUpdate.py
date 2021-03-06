import winreg
import sys
import msvcrt
import os
import platform
import math
import time
import json
import hashlib


# If the module is not found, download it, install it and import it
def SecureImport(module_name):
	try:
		globals()[module_name] = __import__(module_name)
	except ModuleNotFoundError:
		os.system("python -m pip install " + module_name)
		globals()[module_name] = __import__(module_name)


SecureImport("requests")
SecureImport("colorama")
SecureImport("bs4")

BeautifulSoup = bs4.BeautifulSoup


colorama.init()

if os.name != "nt":
	print("[" + colorama.Fore.RED + "ERROR\033[0m] This script is only available for Windows.")
	exit(1)



severity = type("", (), {
"info": 0,
"warn": 1,
"error": 2,
"update_available": 3,
"debug": 4
})

colors = [
type("", (), {"color": colorama.Fore.GREEN, "text": "INFO"}),
type("", (), {"color": colorama.Fore.YELLOW, "text": "WARN"}),
type("", (), {"color": colorama.Fore.RED, "text": "ERROR"}),
type("", (), {"color": colorama.Fore.CYAN, "text": "UPDATE"}),
type("", (), {"color": colorama.Fore.MAGENTA, "text": "DEBUG"})
]


# This list will be filled with detected programs versions
programs = {
"mkvtoolnix": type("", (), {"name": "MKVToolNix", "version": "", "ext": "exe"}),
"putty": type("", (), {"name": "PuTTY", "version": "", "path": "", "ext": "exe"}),
"7zip": type("", (), {"name": "7zip", "version": "", "ext": "exe"}),
"7zip-zstd": type("", (), {"name": "7zip-Zstandard", "version": "", "ext": "exe"}),
"python": type("", (), {"name": "Python", "version": "", "ext": "exe"}),
"vlc": type("", (), {"name": "VLC", "version": "", "ext": "exe"}),
"npp": type("", (), {"name": "Notepad++", "version": "", "ext": "exe"}),
"veracrypt": type("", (), {"name": "VeraCrypt", "version": "", "ext": "exe"}),
"imageglass": type("", (), {"name": "ImageGlass", "version": "", "ext": "msi"}),
"openvpn": type("", (), {"name": "OpenVPN", "version": "", "ext": "msi"}),
"qbittorrent": type("", (), {"name": "qBittorrent", "version": "", "ext": "exe"}),
"hxd": type("", (), {"name": "HxD", "version": "", "ext": "zip"}),
"processhacker": type("", (), {"name": "Process Hacker 2", "version": "", "ext": "exe"})
}

VERSION = "1.2.0"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36"



def Exit(code):
	print("Press any key to close this window...")
	msvcrt.getch()
	exit(code)

def PrintMessage(severity, message, end="\n"):
	print("[" + colors[severity].color + colors[severity].text + "\033[0m] " + message, end=end)



def DoRequest(url):
	try:
		req = requests.get(url, headers={ "user-agent": USER_AGENT }, allow_redirects=True)
		if req.status_code != 200:
			PrintMessage(severity.warn, "HTTP request returned code " + str(req.status_code) + ". This may be temporary or fixed in a new update.")
			raise Skip
		return req.content
		
	except requests.exceptions.RequestException as e:
		PrintMessage(severity.error, str(e))
		raise requests.exceptions.RequestException


def ScrapeFosshubDownloadPage(page, project_name, project_id):
	
	dl = page.find_all("dl")
	data_file = ""
	for element in dl:
		
		tmp = element.find("div").find("a")["data-file"]
		if "64" in tmp:
			data_file = tmp
			break
			
	
	
	if data_file == "":
		return False
	
	file_name = data_file
	scripts = page.find_all("script")
	av_hash_prefix = "setup.exe\",\"r\":\""			# Used to find the antivirus signature for downloading
	av_signature = ""
	for script in scripts:
		script = str(script)
		if av_hash_prefix in str(script):
			av_signature_offset = script.index(av_hash_prefix) + len(av_hash_prefix)
			av_signature = script[av_signature_offset:av_signature_offset + 24]
			break
		
		
	
	
	
	post_data = "{\"projectId\":\"" + project_id + "\",\"releaseId\":\"" + av_signature + "\",\"projectUri\":\"" + project_name + ".html\",\"fileName\":\"" + file_name + "\",\"source\":\"CF\"}"
	
	try:
		req = requests.post("https://api.fosshub.com/download/", headers={ "user-agent": USER_AGENT, "Content-Type": "application/json" }, data=post_data)
	
	except Exception as e:
		PrintMessage(severity.error, str(e))
		Exit(1)
	
	
	
	json_data = json.loads(req.content)
	try:
		json_data = json_data["data"]["url"]
	except Exception as e:
		PrintMessage(severity.error, str(e))
		Exit(1)
	
	return json_data



def DownloadFile(url, path="", user_agent=USER_AGENT):
	
	headers = {}
	if user_agent:
		headers["user-agent"] = user_agent
	
	try:
		req = requests.get(url, headers=headers, stream=True, allow_redirects=True)
		if not path:
			path = os.environ["temp"] + "\\" + hashlib.md5(url.encode()).hexdigest() + ".bin"
		file = open(path, "wb")
		for chunk in req.iter_content(4096):
			file.write(chunk)
		
		file.close()
		return path
		
	except Exception as e:
		PrintMessage(severity.error, str(e))
		Exit(1)


def DownloadSetup(url, program, user_agent=USER_AGENT):
	
	if hasattr(programs[program], "path") and programs[program].path != "":
		path = programs[program].path
	else:
		path = os.environ["temp"] + "\\AutoUpdate-" + programs[program].name + "." + programs[program].ext
	
	return DownloadFile(url, path=path, user_agent=user_agent)


def SearchPath(program):
	paths = os.environ["path"].split(";")
	for path in paths:
		path = path + ("" if path.endswith("\\") else "\\") + program + ".exe"
		if os.path.exists(path) and os.path.isfile(path):
			return path
		
	return False


class Skip(Exception):
	pass


# Getting the online version then decide if we update or not
PrintMessage(severity.info, "Checking for updates...", end="")
latest_version = DoRequest("https://raw.githubusercontent.com/Noelite/AutoUpdate/main/version").decode().rstrip()

if VERSION != latest_version:
	print(" New version available: '" + latest_version + "'")
	while True:
		choice = input("Make update ? [Y/n] ").lower()
		if choice == "" or choice == "y" or choice == "yes":
			print("Downloading update...", end="")
			DownloadFile("https://raw.githubusercontent.com/Noelite/AutoUpdate/main/AutoUpdate.py" + ("c" if __file__.endswith(".pyc") else ""), __file__)
			print(" OK !")
			print("Restarting...")
			if sys.argv[0].endswith(".py") or sys.argv[0].endswith(".pyc"):
				sys.argv.insert(0, "python")
			os.execvp(sys.argv[0], sys.argv)
			
			exit(0)
		
		elif choice == "n" or choice == "no":
			break
		
		else:
			continue

else:
	print(" " + VERSION)



########## MKVTOOLNIX ##########

PrintMessage(severity.info, "Checking MKVToolNix...", end="")
try:

	regkey = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\MKVToolNix")
	regvalue = winreg.QueryValueEx(regkey, "DisplayVersion")
	regkey.Close()
	
	programs["mkvtoolnix"].version = regvalue[0]
	print(" Version: " + programs["mkvtoolnix"].version)
	
	page = BeautifulSoup(DoRequest("https://www.fosshub.com/MKVToolNix.html"), features="html.parser")
	latest_version = page.find("dl").find_all("div")[2].find("dd").text
	
	if programs["mkvtoolnix"].version != latest_version:
		PrintMessage(severity.update_available, "MKVToolNix " + programs["mkvtoolnix"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading MKVToolNix...", end="")
		setup_path = DownloadSetup(ScrapeFosshubDownloadPage(page, "MKVToolNix", "5b8f889d59eee027c3d78aab"), program="mkvtoolnix")
		print(" Done !")
		os.system("\"" + setup_path + "\"")
		

except (FileNotFoundError, OSError):
	print(" Not found.")
except Skip:
	pass



########## PUTTY ##########

PrintMessage(severity.info, "Checking PuTTY...", end="")

path = SearchPath("putty")
if path:
	file = open(path, "rb")
	data = file.read()
	file.close()
	programs["putty"].path = path;
	
	if b"Release " not in data:
		PrintMessage(severity.error, "Unable to determine version, re-downloading it.")
		try:
			os.remove(path)
		except OSError as e:
			PrintMessage(severity.error, str(e))
		
	
	else:
		programs["putty"].version = data[data.find(b"Release ") + 8:data[data.find(b"Release ") + 8:].find(b"\x00") + data.find(b"Release ") + 8].decode("utf-8")
		print(" Version: " + programs["putty"].version)
		
	
	page = BeautifulSoup(DoRequest("https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html"), features="html.parser")
	
	latest_version = page.find("title").text
	latest_version = latest_version[latest_version.index("(") + 1:]
	latest_version = latest_version[0:latest_version.index(")")]
	
	if programs["putty"].version != latest_version:
		PrintMessage(severity.update_available, "PuTTY " + programs["putty"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading PuTTY...", end="")
		DownloadSetup(page.find_all("span", class_="downloadfile")[4].find("a")["href"], program="putty")
		print(" Done !")

else:
	print(" Not found.")




########## 7-Zip ##########

PrintMessage(severity.info, "Checking 7-Zip...", end="")

try:
	regkey = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\7-Zip")
	regvalue = winreg.QueryValueEx(regkey, "DisplayVersion")
	regkey.Close()
	programs["7zip"].version = regvalue[0]
	print(" Version: " + programs["7zip"].version)
	
	page = BeautifulSoup(DoRequest("https://www.7-zip.org/download.html"), features="html.parser")
	latest_version = ""
	
	elements = page.find_all("b")
	for element in elements:
		if element.text.startswith("Download 7-Zip "):
			latest_version = element.text[element.text.index("Download 7-Zip ") + 15:]
			latest_version = latest_version[0:latest_version.index(" ")]
			break
	
	if programs["7zip"].version != latest_version:
		PrintMessage(severity.update_available, "7-Zip " + programs["7zip"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading 7-Zip...", end="")
		
		all_links = page.find_all("a")
		final_link = ""
		for link in all_links:
			target = link["href"]
			if "x64" in target and "linux" not in target:
				if not target.startswith("http"):
					final_link = "https://www.7-zip.org/" + target
				break
			
		if final_link == "":
			PrintMessage(severity.error, "Could not find download url for 7-Zip")
			Exit(1)
		
		setup_path = DownloadSetup(final_link, program="7zip")
		print(" Done !")
		os.system("\"" + setup_path + "\"")


except (FileNotFoundError, OSError):
	print(" Not found.")
except Skip:
	pass




########## 7-Zip Zstandard ##########

PrintMessage(severity.info, "Checking 7-Zip-Zstandard...", end="")

try:
	regkey = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\7-Zip-Zstandard")
	regvalue = winreg.QueryValueEx(regkey, "DisplayVersion")
	regkey.Close()
	programs["7zip-zstd"].version = regvalue[0][0:regvalue[0].index(" ")]
	print(" Version: " + programs["7zip-zstd"].version)
	
	page = BeautifulSoup(DoRequest("https://github.com/mcmilk/7-Zip-zstd/releases/latest"), features="html.parser")
	latest_version = ""
	
	release_title = page.find(class_="d-inline mr-3").text.split()
	for part in release_title:
		if "." in part and part.replace(".", "0").isnumeric():
			latest_version = part
			break
	
	
	
	if programs["7zip-zstd"].version != latest_version:
		PrintMessage(severity.update_available, "7-Zip-Zstandard " + programs["7zip-zstd"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading 7-Zip-Zstandard...", end="")
		
		final_link = ""
		assets_list = page.find("div", class_="Box Box--condensed mt-3")
		assets_list = assets_list.find_all("a")
		
		for link in assets_list:
			if link["href"].endswith(".exe") and "x64" in link["href"] and latest_version in link["href"]:
				final_link = link["href"]
				if final_link.startswith("//"):
					final_link = "https:" + final_link
				elif final_link.startswith("/"):
					final_link = "https://github.com" + final_link
				
				break
			
		if final_link == "":
			PrintMessage(severity.error, "Could not find download url for 7-Zip-Zstandard")
			Exit(1)
		
		print(final_link)
		setup_path = DownloadSetup(final_link, program="7zip-zstd")
		print(" Done !")
		os.system("\"" + setup_path + "\"")


except (FileNotFoundError, OSError):
	print(" Not found.")
except Skip:
	pass




########## PYTHON ##########

PrintMessage(severity.info, "Checking Python...", end="")

programs["python"].version = platform.python_version()
print(" Version: " + programs["python"].version)

page = BeautifulSoup(DoRequest("https://www.python.org/downloads/"), features="html.parser")
download_button = page.find("div", class_="download-os-windows").find("a")

latest_version = download_button.text[download_button.text.index("Download Python ") + 16:]

if programs["python"].version != latest_version:
	PrintMessage(severity.update_available, "Python " + programs["python"].version + " ==> " + latest_version)
	PrintMessage(severity.info, "Downloading Python...", end="")
	setup_path = DownloadSetup(download_button["href"], program="python")
	print(" Done !")
	os.system(setup_path + " /passive PrependPath=1 Include_doc=0 Include_tcltk=0 Include_test=0")	# These parameters will trigger auto installation mode



########## VLC MEDIA PLAYER ##########

PrintMessage(severity.info, "Checking VLC...", end="")

try:
	regkey = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\VideoLAN\\VLC")
	regvalue = winreg.QueryValueEx(regkey, "Version")
	regkey.Close()
	programs["vlc"].version = regvalue[0]
	print(" Version: " + programs["vlc"].version)
	
	page = BeautifulSoup(DoRequest("https://www.videolan.org/vlc/"), features="html.parser")
	
	links = page.find("ul", class_="dropdown-menu dropdown-default platform-icons").find_all("a")
	final_link = ""
	
	for link in links:
		
		if "win64" in link["href"]:
			final_link = link["href"]
			if final_link.startswith("//"):
				final_link = "https:" + final_link
		
	
	if final_link == "":
		PrintMessage(severity.error, "Could not find download button for VLC")
		Exit(1)
	
	latest_version = final_link[final_link.index("/vlc/") + 5:]
	latest_version = latest_version[0:latest_version.index("/win64/")]
	
	if programs["vlc"].version != latest_version:
		PrintMessage(severity.update_available, "VLC " + programs["vlc"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading VLC...", end="")
		setup_path = DownloadSetup(final_link, program="vlc", user_agent=None)
		print(" Done !")
		os.system("\"" + setup_path + "\"")
	


except (FileNotFoundError, OSError):
	print(" Not found.")
except Skip:
	pass




########## NOTEPAD++ ##########

PrintMessage(severity.info, "Checking Notepad++...", end="")

try:
	regkey = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Notepad++")
	regvalue = winreg.QueryValueEx(regkey, "DisplayVersion")
	regkey.Close()
	programs["npp"].version = regvalue[0]
	print(" Version: " + programs["npp"].version)
	
	page = BeautifulSoup(DoRequest("https://notepad-plus-plus.org/downloads/"), features="html.parser")
	
	href_to_latest = page.find("ul", class_="patterns-list").find("a")
	
	latest_version = href_to_latest.text.split()
	for part in latest_version:
		if "." in part:
			
			latest_version = part
			if part.startswith("v"):
				latest_version = part[1:]
			break
	
	if programs["npp"].version != latest_version:
		PrintMessage(severity.update_available, "Notepad++ " + programs["npp"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading Notepad++...", end="")
		
		page = BeautifulSoup(DoRequest(href_to_latest["href"]), features="html.parser")
		
		links = page.find("main", id="main").find_all("a")
		final_link = ""
		for link in links:
			
			if link.text.lower() == "installer":
				if "x64" in link["href"] and link["href"].endswith(".exe"):
					final_link = link["href"]
					break
					
				
			
		
		if final_link == "":
			PrintMessage(severity.error, "Could not find download url for Notepad++")
			Exit(1)
		
		setup_path = DownloadSetup(final_link, program="npp")
		print(" Done !")
		os.system("\"" + setup_path + "\"")
	


except (FileNotFoundError, OSError):
	print(" Not found.")
except Skip:
	pass




########## VERACRYPT ##########

PrintMessage(severity.info, "Checking VeraCrypt...", end="")

try:
	regkey = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\VeraCrypt")
	regvalue = winreg.QueryValueEx(regkey, "DisplayVersion")
	regkey.Close()
	programs["veracrypt"].version = regvalue[0]
	print(" Version: " + programs["veracrypt"].version)
	
	page = BeautifulSoup(DoRequest("https://www.veracrypt.fr/en/Downloads.html"), features="html.parser")
	
	links = page.find_all("a")
	latest_version = ""
	for link in links:
		text = link.text.strip()
		
		if text.startswith("VeraCrypt Setup "):
			latest_version = text[16:]
			latest_version = latest_version[0:latest_version.index(".exe")]
			break
	
	if latest_version == "":
		PrintMessage(severity.error, "Could not find download url for VeraCrypt")
		Exit(1)
	
	if programs["veracrypt"].version != latest_version:
		PrintMessage(severity.update_available, "VeraCrypt " + programs["veracrypt"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading VeraCrypt...", end="")
		setup_path = DownloadSetup(page.find_all("ul")[1].find("a")["href"], program="veracrypt")
		print(" Done !")
		os.system("\"" + setup_path + "\"")
	

except (FileNotFoundError, OSError):
	print(" Not found.")
except Skip:
	pass




########## IMAGEGLASS ##########

PrintMessage(severity.info, "Checking ImageGlass...", end="")

try:
	regkey = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall")
	regvalue = None
	i = 0
	
	while True:
		subkey = winreg.EnumKey(regkey, i)
		subkey = winreg.OpenKeyEx(regkey, subkey)
		
		try:
			value = winreg.QueryValueEx(subkey, "DisplayName")
		
		except FileNotFoundError:
			pass
		
		if value[0] == "ImageGlass":
			regvalue = winreg.QueryValueEx(subkey, "DisplayVersion")
			subkey.Close()
			break
		subkey.Close()
		i += 1
		
		
		
	if not regvalue:
		raise FileNotFoundError
	
	regkey.Close()
	programs["imageglass"].version = regvalue[0]
	print(" Version: " + programs["imageglass"].version)
	
	page = BeautifulSoup(DoRequest("https://imageglass.org/releases"), features="html.parser")
	
	latest_release = page.find("ul", class_="article-list").find("li")
	
	latest_version = latest_release.text[latest_release.text.index("Version: ") + 9:]
	latest_version = latest_version[0:latest_version.index("\n")]
	
	if programs["imageglass"].version != latest_version:
		PrintMessage(severity.update_available, "ImageGlass " + programs["imageglass"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading ImageGlass...", end="")
		
		page = BeautifulSoup(DoRequest(latest_release.find("a")["href"]), features="html.parser")
		x64_installer = page.find_all("div", "download-file-item")
		last_download_page = ""
		for element in x64_installer:
			
			if "installer x64" in element.text:
				last_download_page = element.find("a")["href"]
				break
			
		
		if last_download_page == "":
			PrintMessage(severity.warn, "Could not find download url for ImageGlass")
			raise Skip
		
		
		setup_path = DownloadSetup(last_download_page.replace("/download", "") + "/download", program="imageglass")
		print(" Done !")
		os.system("\"" + setup_path + "\"")


except (FileNotFoundError, OSError):
	print(" Not found.")
except Skip:
	pass



########## OPENVPN ##########

PrintMessage(severity.info, "Checking OpenVPN...", end="")

try:
	regkey = winreg.OpenKeyEx(winreg.HKEY_CLASSES_ROOT, "Installer\\Products")
	value = None
	try:
		i = 0
		while True:
			subkey = winreg.EnumKey(regkey, i)
			subkey = winreg.OpenKeyEx(regkey, subkey)
			
			try:
				value = winreg.QueryValueEx(subkey, "ProductName")
			except OSError:
				pass
			
			if value[0].startswith("OpenVPN") and len(value[0]) > 15:
				value = value[0][8:]
				value = value[0:value.find("-")]
				programs["openvpn"].version = value
				subkey.Close()
				break
			subkey.Close()
			i += 1
	except OSError:
		pass
	
	if not programs["openvpn"].version:
		raise FileNotFoundError
	
	
	regkey.Close()
	print(" Version: " + programs["openvpn"].version)
	
	page = BeautifulSoup(DoRequest("https://openvpn.net/community-downloads/"), features="html.parser")
	
	latest_release = page.find("div", class_="card")
	
	latest_version = latest_release.text[latest_release.text.index("OpenVPN ") + 8:]
	latest_version = latest_version[0:latest_version.index(" ")]
	
	if programs["openvpn"].version != latest_version:
		PrintMessage(severity.update_available, "OpenVPN " + programs["openvpn"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading OpenVPN...", end="")
		
		final_link = ""
		links_table = latest_release.find_all("tr")
		for row in links_table:
			
			text = row.text.lower()
			if "windows" in text and "64" in text and "installer" in text:
				links = row.find_all("a")
				for link in links:
					if link["href"].endswith(".msi"):
						final_link = link["href"]
						break
					
			if final_link != "":
				break
				
				
		if final_link == "":
			PrintMessage(severity.error, "Could not find download url for OpenVPN")
			Exit(1)
		
		
		setup_path = DownloadSetup(final_link, program="openvpn")
		print(" Done !")
		os.system("\"" + setup_path + "\"")


	
except (FileNotFoundError, OSError):
	print(" Not found.")
except Skip:
	pass



########## QBITTORRENT ##########

PrintMessage(severity.info, "Checking qBittorrent...", end="")

try:
	regkey = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\qBittorrent")
	regvalue = winreg.QueryValueEx(regkey, "DisplayVersion")
	regkey.Close()
	programs["qbittorrent"].version = regvalue[0]
	print(" Version: " + programs["qbittorrent"].version)
	
	page = BeautifulSoup(DoRequest("https://www.fosshub.com/qBittorrent.html"), features="html.parser")
	
	latest_version = page.find("dl").find_all("div")[2].find("dd").text
	
	if programs["qbittorrent"].version != latest_version:
		PrintMessage(severity.update_available, "qBittorrent " + programs["qbittorrent"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading qBittorrent...", end="")
		setup_path = DownloadSetup(ScrapeFosshubDownloadPage(page, "qBittorrent", "5b8793a7f9ee5a5c3e97a3b2"), program="qbittorrent")
		print(" Done !")
		os.system("\"" + setup_path + "\"")
		

except (FileNotFoundError, OSError):
	print(" Not found.")
except Skip:
	pass



########## HXD ##########

PrintMessage(severity.info, "Checking HxD...", end="")

try:
	regkey = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\HxD_is1")
	regvalue = winreg.QueryValueEx(regkey, "DisplayVersion")
	regkey.Close()
	programs["hxd"].version = regvalue[0]
	print(" Version: " + programs["hxd"].version)
	
	page = BeautifulSoup(DoRequest("https://mh-nexus.de/en/downloads.php?product=HxD20"), features="html.parser")
	
	latest_version = page.find("tbody").find_all("tr")[1].find_all("td")[2].text.strip()
	latest_version = latest_version.split(".")
	latest_version = latest_version[0] + "." + latest_version[1]
	
	if programs["hxd"].version != latest_version:
		PrintMessage(severity.update_available, "HxD " + programs["hxd"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading HxD...", end="")
		setup_path = DownloadSetup("https://mh-nexus.de/downloads/HxDSetup.zip", program="hxd")
		print(" Done !")
		os.system("\"" + setup_path + "\"")


except (FileNotFoundError, OSError):
	print(" Not found.")
except Skip:
	pass



########## PROCESS HACKER 2 ##########

PrintMessage(severity.info, "Checking Process Hacker 2...", end="")

try:
	regkey = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Process_Hacker2_is1")
	regvalue = winreg.QueryValueEx(regkey, "DisplayName")
	regkey.Close()
	programs["processhacker"].version = regvalue[0][15:]
	programs["processhacker"].version = programs["processhacker"].version[0:programs["processhacker"].version.index(" ")]
	print(" Version: " + programs["processhacker"].version)
	
	page = BeautifulSoup(DoRequest("https://processhacker.sourceforge.io/downloads.php"), features="html.parser")
	
	final_link = page.find("a", class_="text-left")["href"]
	latest_version = final_link[final_link.index("/processhacker-") + 15:]
	latest_version = latest_version[0:latest_version.index("-setup")]
	
	
	if programs["processhacker"].version != latest_version:
		PrintMessage(severity.update_available, "Process Hacker " + programs["processhacker"].version + " ==> " + latest_version)
		PrintMessage(severity.info, "Downloading Process Hacker...", end="")
		setup_path = DownloadSetup(final_link, program="processhacker", user_agent=None)
		print(" Done !")
		os.system("\"" + setup_path + "\"")


except (FileNotFoundError, OSError):
	print(" Not found.")
except Skip:
	pass




print()
i = 2
while i:
	print("\rClosing in " + str(i) + " second" + ("s..." if i > 1 else "... "), end="")
	time.sleep(1)
	i -= 1

print()
exit(0)
