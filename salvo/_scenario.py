import sys
import asyncio
import time
import base64
from collections import namedtuple
from aiohttp import ClientResponseError

from salvo.util import resolve

import molotov
from molotov.run import run
from molotov import util, api


@molotov.setup()
async def init_worker(worker_num, args):
    headers = {}

    content_type = molotov.get_var("content_type")
    if content_type:
        headers["Content-Type"] = content_type

    auth = molotov.get_var("auth")
    if auth is not None:
        basic = base64.b64encode(auth.encode())
        headers["Authorization"] = "Basic %s" % basic.decode()

    return {"headers": headers}


@molotov.scenario()
async def http_test(session):
    url = molotov.get_var("url")
    res = molotov.get_var("results")
    meth = molotov.get_var("method")

    options = {}
    pre_hook = molotov.get_var("pre_hook")
    if pre_hook is not None:
        meth, url, options = pre_hook(meth, url, options)
    post_hook = molotov.get_var("post_hook")
    data = molotov.get_var("data")
    if data:
        if callable(data):
            result = data(
                meth, url, {**options, "data_args": molotov.get_var("data_args")}
            )
            if type(result) == tuple:  # Deal with multipart/form-data
                session.headers.update(result[0])
                options["data"] = result[1]
            else:
                options["data"] = result
        else:
            options["data"] = data

    meth = getattr(session, meth.lower())
    start = time.time()
    try:
        # XXX we should implement raise_for_status globally in
        # the session in Molotov
        async with meth(url, raise_for_status=True, **options) as resp:
            # print(f"Respuesta recibida: {resp.status} {resp.reason}")
            # print(f"Recibido {resp.headers['content-type']} de longitud {len(txt)}  en la respuesta")
            if post_hook is not None:
                resp = await post_hook(resp)
            else:
                # Read the response, to account for the network bandwidth
                txt = await resp.read()
            res.incr(resp.status, time.time() - start)
    except ClientResponseError as exc:
        print("EXCEPCION:", exc)
        res.incr(exc.status, time.time() - start)
        res.errors[exc.status] += 1
        if exc.message not in res.errors_desc:
            res.errors_desc[exc.message] = exc


#    except Exception as exc:
#        print("EXCEPCION GENERAL:", exc)
