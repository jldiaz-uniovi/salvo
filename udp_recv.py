import socket
import sys
import threading
import time
import statistics
from dataclasses import dataclass
from typing import List

"""
molotov.atc33.GET.156.35.151.156./detect:5|ms
molotov.atc33.GET.156.35.151.156./detect.200:1|c
"""

class Stats:
    times: List[int] = []
    requests: float = 0
    threads: int = 0

stats = Stats()

def update_stats(line, lock: threading.Lock):
    aux, unit = line.strip().split("|")
    value = float(aux.split(":")[-1])
    with lock:
        if unit == "c":
            stats.requests += value
        elif unit == "ms":
            stats.times.append(value)
        elif unit == "g":
            stats.threads = int(value)
        else:
            print(line)


def reset_stats():
    stats.times = []
    stats.requests = 0
    stats.threads = 0


def compute_stats(lock: threading.Lock):
    with lock:
        times = stats.times.copy()
        requests = stats.requests
        threads = stats.threads
        reset_stats()
    
    count = len(times)
    if count:
        avg = statistics.fmean(times)
        std = statistics.pstdev(times)
        print(f"{threads}\t{count}\t{avg}\t{std}")


def dump_stats(lock):
    print("Concurrency\t# Requests\tAvg response time (ms)\tStdev response time")
    while True:
        compute_stats(lock)
        time.sleep(1)


def main():
    l = threading.Lock()
    t = threading.Thread(target=udp_server, args=(l,))
    t.start()
    t2 = threading.Thread(target=dump_stats, args=(l,))
    t2.start()
    t.join()
    t2.join()

def udp_server(lock):
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 9000
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("", port))
    while True:
        b, a = s.recvfrom(2000)
        line = b.decode("utf-8")
        update_stats(line, lock)


if __name__ == "__main__":
    main()