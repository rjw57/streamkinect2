#!/usr/bin/env python

import os
from setuptools import setup, find_packages

# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "streamkinect2",
    version = "0.0.1",
    author = "Rich Wareham",
    author_email = "rich.streamkinect2@richwareham.com",
    description = "A simple network streamer for kinect2 data.",
    license = "BSD",
    keywords = "kinect kinect2 zeroconf bonjour",
    url = "https://github.com/rjw57/stramkinect2",
    packages=find_packages(exclude='test'),
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],

    install_requires=[
        'zeroconf', 'pyzmq',
    ],

    setup_requires=[
        'nose',
    ],

    tests_require=[
        'coverage'
    ],
)
