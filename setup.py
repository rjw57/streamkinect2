#!/usr/bin/env python

import os
from setuptools import setup, find_packages

import streamkinect2.version as meta

# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = meta.__project__,
    version = meta.__version__,
    author = meta.__author__,
    author_email = meta.__author_email__,
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
        'blinker',
        'enum34',
        'lz4',
        'numpy',
        'pillow',
        'pyzmq',
        'tornado',
        'zeroconf',
    ],

    setup_requires=[
        'nose',
    ],

    tests_require=[
        'coverage'
    ],

    extras_require={
        'docs': [ 'sphinx', 'docutils', ],
    },
)
