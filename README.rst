=====
iodid
=====

This is heavily based on https://github.com/tarekziade/salvo, slightly adapted to fit my own needs. 
The most important modifications are aimed at:

* Injecting a load given as a series of rps
* Allowing the use of multipart/form-data (eg: uploading files) as part of POST requests

Installation
============

iodid requires Python 3.6+ and **Molotov**, which gets installed as a
dependency.

Just clone this respository and do::

    $ pip install .


Basic usage
===========

(TODO: Document the new features, what follows is simply taken from salvo README)

Basic usage example: 100 queries with a maximum concurrency of 10 users::

    % iodid http://localhost:80 -c 10 -n 100
    -------- Server info --------

    Server Software: nginx/1.18.0
    Host: localhost

    -------- Running 100 queries - concurrency 10 --------

    [================================================================>.] 99%

    -------- Results --------

    Successful calls    		1000
    Total time          		16.0587 s
    Average             		0.0161 s
    Fastest             		0.0036 s
    Slowest             		0.2524 s
    Amplitude           		0.2488 s
    Standard deviation  		0.011326
    Requests Per Second 		62.27
    Requests Per Minute 		3736.29

    -------- Status codes --------
    Code 200          		1000 times.


You can also use `--duration` if you want to run for a given amount of time.

For a full list of features, run `iodid --help`
