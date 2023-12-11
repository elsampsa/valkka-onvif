"""

::

    pip install --user bs4 urllib3

"""
import os, re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def download_files(url, ext=".wsdl", save_folder="."):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            if ext in href:
                wsdl_url = urljoin(url, href)
                fname=wsdl_url.split("/")[-1].split("?")[0] # https://some/path/filename.ext?something --> filename.ext?something --> filename.ext
                path = os.path.join(save_folder, fname)
                # print(f"Downloading {wsdl_url} to {path}")
                with requests.get(wsdl_url, stream=True) as wsdl_response:
                    with open(path, 'wb') as f:
                        for chunk in wsdl_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                print(f"Downloaded {wsdl_url}")


def download_deps(folder_path=".", cache = [], iter = 0):
    """Find dependencies, download new files, find their dependencies and download them, etc. recursively
    """
    print("\ndownloading dependencies: iteration", iter)
    got_new = False
    for filename in os.listdir(folder_path):
        if filename.endswith(".wsdl") or filename.endswith(".xsd"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            rest=r'schemaLocation="(http.*)"'
            reg=re.compile(rest)
            for url in reg.findall(content):
                if url not in cache:
                    got_new = True
                    print("downloading from new url", url)
                    os.system(f"curl -O {url}")
                    cache.append(url)
    if got_new:
        download_deps(folder_path = folder_path, cache = cache, iter = iter + 1)

def update_schema_locations(folder_path="."):
    for filename in os.listdir(folder_path):
        if filename.endswith(".wsdl") or filename.endswith(".xsd"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            rest=r'schemaLocation=\"(.*)\/(\S*.\w{3,4})\"'
            reg=re.compile(rest)
            # m=reg.search(content)
            #print("m>",m)
            #print("g1>",m.group(1))
            #print("g2>",m.group(2))
            updated_content = re.sub(reg, 'schemaLocation="./\\2"', content)

            # Write the updated content back to the file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)

            print(f"Updated schemaLocation paths in {filename}")


def get_basic():
    """This list is not complete.. better to snoop them from the actual files
    """
    raise(BaseException("do not use"))
    lis=[
        "http://www.w3.org/2005/05/xmlmime",
        "http://www.w3.org/2003/05/soap-envelope",
        "http://www.w3.org/2004/08/xop/include",
        "http://schemas.xmlsoap.org/ws/2004/08/addressing"
    ]
    for url in lis:
        print("fetching", url)
        os.system(f"curl -O {url}")


print("\nDOWNLOADING WSDL FILES\n")
download_files("https://www.onvif.org/profiles/specifications/", ext=".wsdl", save_folder=".")

print("\nDOWNLOADING XSD FILES\n")
download_files("https://www.onvif.org/profiles/specifications/", ext=".xsd", save_folder=".")

print("\nDOWNLOADING DEPENDENCIES\n")
download_deps()

print("\nMODIFYING SCHEMA LOCATIONS\n")
update_schema_locations()
