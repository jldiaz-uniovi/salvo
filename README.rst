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

Just clone this repository and do::

    $ pip install .


Basic usage (stress testing)
============================

Basic usage example: 100 queries with a maximum concurrency of 10 users::

    $ iodid http://localhost:80 -c 10 -n 100
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

Usage as trace loader
=====================

To use ``iodid`` as a trace loader you have to use two command line options:

* ``-u N`` to set the time unit (length of the time slot) to N seconds.
  The default if omitted is 1 second.
* ``--trace filename`` to specify the name of the file containing the trace.
* ``-e fraction`` is the fraction of the timeslot in which all requests are
  sent. By default it is 0.0 which means that all requests for that timeslot
  are sent just when the timeslot starts. More on this later.



The trace file simply contains a number per line. Empty lines and lines which
start with ``#`` are ignored. One line containing only the keyword ``END`` causes
the injection to terminate (and the remaining of the file being ignored).

Iodid will run a loop in which each N seconds:

* A new line of the trace file is read, containing the number of requests (M)
  to be performed in the next timeslot.
* A new thread is started. Within this thread:

  * M requests are run concurrently (the client implements asynchronously this part
    so all requests are run in the same thread). All requests will be GET requests
    by default, unless ``-m`` option is used to specify another kind of request
    (see next section)
  * When all M requests are terminated, the thread ends

Note that if the M requests cannot be served within the N seconds allotted to the timeslot,
the thread for the next timeslot will be added to the one still running for the previous
timeslot. If the server cannot respond quick enough, the threads can pile up in the client.
It is advised to perform previously a stress test to check how many request can the server
handle in a timeslot.

Option ``-e`` can influence the shape of the load received by the server. The default
value (0.0) causes all M requests for the timeslot to be sent at the beginning of the
timeslot. This will cause punctual and repetitive spikes in the server, which are not
very realistic. If ``-e 1.0`` is used instead, the M requests are evenly spaced within the
N seconds of the timeslot. This is more realistic, but it will cause some request to be
launched just at the end of the timeslot, which will overlap with the ones in the next
timeslot. You can aso give other values such as ``-e 0.8`` which will cause that all the
M requests of the timeslot will be launched at regular spaces within the first 0.8*N seconds
of the timeslot. This will leave some time at the end of the timeslot to process the 
pending requests before starting a new timeslot.


POSTing files 
=============

iodid can perform multipart-form posts to upload files (e.g.: images) to a given URL via POST, 
thanks to the extension module `load_image.py` (which must be present in the `PYTHONPATH` folder).

To use it you have to specify several options:

* ``-m POST`` to specify the http verb to use
* ``-D py:load_image.form`` to load from the extension module the function which implements 
  the multipart form protocol.
* ``--data-args`` to specify the keys and values of the HTTP form to be sent. After this option it
  is expected a string composed of several space-separated pairs ``key:value``. For example, 
  ``"model:x kind:test"`` will send an HTTP FORM with two fields named "model" and "kind", and the
  values "x" and "test" for those fields.

  Is the name of a field is ``"file"``, the value is supposed to be the name of a file in the
  same folder. In this case iodide will open that file and send the contents encoded using the
  multipart-form protocol. For example: ``--data-args "file:test_file.jpg"`` would send a test
  image.


You can use this feature as part of a stress test. For example, to perform 100 requests which upload
a test image via POST, with a maximum of 10 concurrent POSTs, you'll do:

    PYTHONPATH=$(pwd) iodid http://localhost:5000 \
      -m POST -D py:load_image.form --data-args "file:test_image.jpg" \
      -c 10 -n 100

You can also use this feature as part of a trace load. All requests performed
in a timeslot will share the same http verb and FORM data. For example:

    PYTHONPATH=$(pwd) iodid http://localhost:5000 \
      -m POST -D py:load_image.form --data-args "file:test_image.jpg" \
      --trace sample.trace -u 5 \

will read a line of ``sample.trace`` each 5 seconds, and will do as many POSTs
as the number in that line, all uploading the same ``test_image.jpg`` file.

Monitoring
==========

``iodid`` is instrumented and when the appropriate options are set it will communicate with an external
statsd server, which can be used in collaboration with other tools to get real time information about
the number of requests, the response times, etc.

The options are:

* ``--statsd`` to activate this functionality
* ``--statsd-address udp://127.0.0.1:9125`` to specify the ip and port of the statsd server to which the info is sent.

One possible setup is to have in the same machine than ``iodid`` a statsd exporter for prometheus:

    $ docker run -d -p 9102:9102 -p 9125:9125 -p 9125:9125/udp prom/statsd-exporter

which can be pulled by prometheus at port 9102 to extract the statistics and further process them or visualize with Grafana.
