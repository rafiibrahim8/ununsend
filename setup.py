from setuptools import setup, find_packages
from zipfile import ZipFile
from os.path import expanduser
from os import makedirs
from ununsend import __version__, __static_path, __template_path


def read_file(filename, lines=False):
    try:
        with open(filename, "r") as f:
            if lines:
                return [i.strip() for i in f.read().split('\n') if i.strip()]
            return f.read()
    except:
        print("Can not read file:", filename)
        return None

def post_install_stuffs():
    static_path = expanduser(__static_path)
    template_path = expanduser(__template_path)
    makedirs(static_path, exist_ok=True)
    makedirs(template_path, exist_ok=True)
    
    try:
        with ZipFile('website_files/static.zip','r') as f:
            f.extractall(path=static_path)
        with ZipFile('website_files/templates.zip','r') as f:
            f.extractall(path=template_path)
        return True
    except:
        return False

long_description = read_file("README.md")

setup(
    name="ununsend",
    version=__version__,
    author="Ibrahim Rafi",
    author_email="me@ibrahimrafi.me",
    license="MIT",
    url="https://github.com/rafiibrahim8/ununsend",
    download_url="https://github.com/rafiibrahim8/ununsend/archive/v{}.tar.gz".format(
        __version__
    ),
    install_requires=read_file('requirements.txt', True),
    description="View messages that were unsent on Messenger.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=["ununsend", "Messenger", "Unsend"],
    packages=find_packages(),
    entry_points=dict(console_scripts=["ununsend=ununsend.ununsend:main"]),
    platforms=["any"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)

print('Performing post setup stuffs...')
if post_install_stuffs():
    print('Post install successful.')
else:
    print('Post install failed. Try reinstalling the package.')

