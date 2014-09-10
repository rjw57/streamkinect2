# Network streaming of Kinect v2 data

[![Build Status](https://travis-ci.org/rjw57/streamkinect2.svg?branch=master)](https://travis-ci.org/rjw57/streamkinect2)

This project is an *experiment* in streaming data from the Kinect 2 sensor to
another host on the network. I need it since the Kinect 2 SDK is only supported
in Windows but the rest of my pipeline is Linux based.

## Notable features

* Simple Python API.
* Zero-configuration setup: uses Zeroconf/Bonjour to automatically discover servers on the network.
* Transparently compresses depth data to reduce bandwidth utilisation.
* Uses [ZeroMQ](http://zeromq.org/) as a high-performance portable transport.
* Tested (using a mock device) with an aim for >95% code coverage.

## Licence

This software is released under a BSD 2 clause license. See the
[COPYING](COPYING.txt) file.
