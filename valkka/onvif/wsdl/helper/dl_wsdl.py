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
                # https://www.onvif.org/ver20/media/wsdl/media.wsdl
                r=re.compile(r'ver(\d\d)')
                m=r.search(wsdl_url)
                ver=m.group(1)
                fname=wsdl_url.split("/")[-1].split("?")[0] # https://some/path/filename.ext?something --> filename.ext?something --> filename.ext
                name, ext = fname.split(".")
                fname = f"{name}-{ver}.{ext}"
                path = os.path.join(save_folder, fname)
                # print(f"Downloading {wsdl_url} to {path}")
                with requests.get(wsdl_url, stream=True) as wsdl_response:
                    with open(path, 'wb') as f:
                        for chunk in wsdl_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                print(f"Downloaded {wsdl_url} into {fname}")


def download_deps(folder_path=".", cache = [], iter = 0):
    """Find dependencies, download new files, find their dependencies and download them, etc. recursively

    Onvif versioning should be renamed like this:

    http://www.onvif.org/onvif/ver10/schema/onvif.xsd -> onvif-10.xsd
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
                    print("\ndownloading from new url", url)
                    target_filename=url.split("/")[-1] 
                    r=re.compile(r'http:\/\/www.onvif.org\/onvif\/ver(\d\d)\/')
                    m=r.search(url) # check if it's an onvif file with version number
                    if not m:
                        r=re.compile(r'http:\/\/www.onvif.org\/ver(\d\d)\/') # another flavor..
                        m=r.search(url) # check if it's an onvif file with version number
                    if m:
                        ver=m.group(1)
                        name, ext = target_filename.split(".")
                        target_filename = f"{name}-{ver}.{ext}"
                    print(f"target filename: {target_filename}")
                    os.system(f"curl -L -o {target_filename} {url}")
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

            """
            # Write the updated content back to the file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)

            print(f"Updated schemaLocation paths in {filename}")
            """

def update_schema_locations2(folder_path="."):
    # verbose=True
    verbose=False
    for filename in os.listdir(folder_path):
        if filename.endswith(".wsdl") or filename.endswith(".xsd"):
            if "accesscontrol-10.wsdl" not in filename:
                #print("skipping", filename)
                #continue
                pass
            file_path = os.path.join(folder_path, filename)
            print("file:", file_path)
            with open(file_path, 'r', encoding='utf-8') as file:
                newlines=[]
                for line in file:
                    #print(line)
                    # rest=r'schemaLocation=\"(.*)\/(\S*.\w{3,4})\"' 
                    # but sometimes that is not the case..
                    # <xs:import namespace="http://www.onvif.org/ver10/pacs" schemaLocation="types.xsd"/>
                    # that should actually be..
                    # <xs:import namespace="http://www.onvif.org/ver10/pacs" schemaLocation="../../ver10/types.xsd"/>
                    # just better to take the version from namespace and only filename from "schemaLocation" field
                    # rest=r'namespace=\"(.*)\".*schemaLocation=\"(.*)"'
                    # and finally, we still have cases where namespace is missing: <xs:include schemaLocation="common.xsd"/>
                    if ("schemaLocation" in line) and ("namespace" not in line):
                        print("\nWARNING: found addressing without namespace")
                        print("You might need to copy file manually to this filename")
                        print(line)
                    rest=r'namespace="([^"]*)"(?:(?!modified="true")[^"])*schemaLocation="([^"]*)"'
                    reg=re.compile(rest)
                    while True:
                        m=reg.search(line)
                        if m:
                            if verbose:
                                print("line>", line)
                                print("m>>",m.group()) # the whole match #
                                print("g1>",m.group(1)) # namespace #
                                print("g2>",m.group(2)) # filename #
                            all=m.group()
                            namespace=m.group(1)
                            fname=m.group(2).split("/")[-1] # take last part of the path
                            m_ver=re.compile("\/ver(\d\d)\/").search(namespace)
                            if m_ver:
                                if verbose: print(">>", m_ver.group(1))
                                ver=m_ver.group(1)
                                name, ext = fname.split(".")
                                fname = f"{name}-{ver}.{ext}"
                            if verbose: print("fname>", fname) # onvif-10.xsd
                            news=f'namespace="{namespace}" modified="true" schemaLocation="{fname}"'
                            line=line.replace(all, news)
                            if verbose: print("final>",line)
                        else:
                            newlines.append(line)
                            break
            # with open(file_path+".tmp", 'w', encoding='utf-8') as file:
            with open(file_path, 'w', encoding='utf-8') as file:
                for line in newlines:
                    file.write(line)



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
update_schema_locations2()

print("\nMAKING ADDITIONAL COPIES")
os.system("cp -f common-10.xsd common.xsd")

