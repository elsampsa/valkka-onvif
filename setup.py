from setuptools import setup, Extension, find_packages
import sys

# modified by setver.bash
version = '1.6.7'

setup(
    name = "valkka-onvif",
    version = version,
    install_requires = [
        'zeep == 4.0.0',
        'httpx == 0.25.0', # seems to be missing from zeep's dependencies?
        'netifaces', # required for discovery
        'PYAML'
    ],
    # packages = find_packages(), # # includes python code from every directory that has an "__init__.py" file in it.  If no "__init__.py" is found, the directory is omitted.  Other directories / files to be included, are defined in the MANIFEST.in file
    # this is needed for namespace packages:
    packages=[
        'valkka.onvif',
        'valkka.onvif.multiprocess',
        'valkka.discovery',
        'valkka.discovery.wsdiscovery',
        'valkka.discovery.wsdiscovery.actions',
        'valkka.discovery.camsearch',
        ],
    
    include_package_data=True, # # conclusion: NEVER forget this : files get included but not installed
    # # "package_data" keyword is a practical joke: use MANIFEST.in instead

    entry_points={
        'console_scripts': [
            'valkka-camsearch = valkka.discovery.camsearch.cli:main',
        ]
    },

    # metadata for upload to PyPI
    author = "Sampsa Riikonen",
    author_email = "sampsa.riikonen@iki.fi",
    description = "Onvif python dependencies for libValkka",
    license = "MIT",
    keywords = "valkka video surveillance onvif",
    url = "https://elsampsa.github.io/valkka-examples/_build/html/onvif.html",

    long_description ="""
    Onvif python dependencies for libValkka
    """,
    long_description_content_type='text/plain',

    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Topic :: Multimedia :: Video',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
    ],
    project_urls={
        'Valkka library': 'https://elsampsa.github.io/valkka-examples/'
    }
)
