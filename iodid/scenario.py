import sys
import asyncio
import time
import base64
from collections import namedtuple
from aiohttp import ClientResponseError

from iodid.util import resolve

import molotov
from molotov.run import run
from molotov import util, api


def run_test(url, results, iodidargs):
    args = namedtuple("args", "")
    args.force_shutdown = False
    args.ramp_up = 0.0
    args.verbose = iodidargs.verbose
    args.quiet = iodidargs.quiet
    args.exception = False
    args.processes = 1
    args.debug = False
    args.workers = iodidargs.concurrency
    args.console = True
    args.statsd = iodidargs.statsd
    args.statsd_address = iodidargs.statsd_address
    args.single_mode = None
    if iodidargs.duration:
        args.duration = iodidargs.duration
        args.max_runs = None
    else:
        args.duration = 9999
        args.max_runs = iodidargs.requests
    args.delay = 0.0
    args.sizing = False
    args.sizing_tolerance = 0.0
    args.console_update = 0.1
    args.use_extension = []
    args.fail = None
    args.force_reconnection = False
    args.scenario = __file__.replace("scenario", "_scenario")  # "_scenario.py"
    args.disable_dns_resolve = False
    args.single_run = False

    molotov.set_var("method", iodidargs.method)
    molotov.set_var("url", url)
    molotov.set_var("results", results)
    molotov.set_var("auth", iodidargs.auth)
    molotov.set_var("content_type", iodidargs.content_type)
    molotov.set_var("data_args", iodidargs.data_args)

    data = iodidargs.data
    if data and data.startswith("py:"):
        data = resolve(data.split(":")[1])
    molotov.set_var("data", data)

    if iodidargs.pre_hook is not None:
        molotov.set_var("pre_hook", resolve(iodidargs.pre_hook))
    else:
        molotov.set_var("pre_hook", None)

    if iodidargs.post_hook is not None:
        post_hook = resolve(iodidargs.post_hook)
        if not asyncio.iscoroutinefunction(post_hook):
            raise Exception("The post hook needs to be a coroutine")
        molotov.set_var("post_hook", post_hook)
    else:
        molotov.set_var("post_hook", None)

    class Stream:
        def __init__(self):
            self.buffer = []

        def write(self, msg):
            self.buffer.append(msg)

        def flush(self):
            pass

    # this module is going to be loaded by molotov,
    # so we need to clear up its internal state
    # XXX we should have a better way to do this
    util._STOP = False
    util._STOP_WHY = []
    util._TIMER = None
    api._SCENARIO.clear()
    api._FIXTURES.clear()

    stream = Stream()
    res = run(args, stream=stream)

    if res["SETUP_FAILED"] > 0 or res["SESSION_SETUP_FAILED"] > 0:
        print("Setup failed. read the Molotov session below to get the error")
        print("".join(stream.buffer))

    return res
