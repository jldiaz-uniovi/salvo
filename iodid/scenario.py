import sys
import asyncio
import time
import base64
from collections import namedtuple
from aiohttp import ClientResponseError
from copy import copy
import threading
import os

from iodid.util import resolve
from iodid.output import RunResults

import molotov
from molotov.run import run
from molotov.runner import Runner
from molotov import util, api
from molotov.stats import get_statsd_client
from aiodogstatsd import Client


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


def monkeypatched_launch_processes(self):
    args = self.args
    args.original_pid = os.getpid()
    self._process()
    return self._results


Runner._launch_processes = monkeypatched_launch_processes


class WorkloadTest:
    def __init__(self, url, workload, time_unit, args):
        self.url = url
        self.workload = workload
        self.time_unit = time_unit
        self.args = copy(args)
        self.res = []
        self.threads = []
        if self.args.statsd:
            self.statsd = get_statsd_client(self.args.statsd_address)
            self.lock = threading.Lock()
            self.num_threads = 0
        else:
            self.statsd = None

    def run(self):
        self.thread = threading.Thread(target=self.periodic)
        self.thread.daemon = False
        self.thread.start()
        self.thread.join()
        for thread in self.threads:
            thread.join()
        return self.res

    async def update_statsd_numthreads(self, increment=True):
        if not self.statsd:
            return
        with self.lock:
            if increment:
                self.num_threads += 1
            else:
                self.num_threads -= 1
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async with self.statsd as f:
            f.gauge("iodid_num_threads", value=self.num_threads)

    def inject_workload(self, t, wl):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.update_statsd_numthreads(increment=True))
        self.args.concurrency = wl
        self.args.requests = 1
        res = RunResults(quiet=True)
        molores = run_test(self.url, res, self.args)
        print(f"[{t}] Resultados molotov: {molores}")
        print(f"[{t}] Estadísticas recopiladas: {res.get_json()}")
        self.res.append(res)
        loop.run_until_complete(self.update_statsd_numthreads(increment=False))

    def periodic(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for t, wl in enumerate(self.workload):
            print(f"Timeslot {t}. Workload {wl}")
            thread = threading.Thread(target=self.inject_workload, args=(t, wl))
            self.threads.append(thread)
            thread.start()
            time.sleep(self.time_unit)
