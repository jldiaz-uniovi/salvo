class LazyTrace:
    """Implements a lazy reader for a trace file. The file is not open until
    an attempt of iteration is made over this object. At each iteration one
    line of the file is read and parsed, and the resulting integer is returned.

    Empty lines or lines which begin by "#" are skipped in the iterations.

    Lines that cannot be parsed as integers produce a warning and are skipped too.

    Usage example:

    ```
    t = LazyTrace("example.trace")
    for n in t:
        print(n)
    ```
    """

    def __init__(self, filename):
        self.filename = filename
        self._file = None
        self._ln = 0

    def __iter__(self):
        if self._file is not None:
            self._file.close()
            self._ln = 0
        self._file = open(self.filename)
        return self

    def __next__(self):
        if self._file is None:
            raise StopIteration()
        try:
            ok = False
            while not ok:
                line = next(self._file)
                self._ln += 1
                if line.startswith("#") and "ENDTRACE" in line:
                    raise StopIteration()
                if not line.strip() or line.startswith("#"):
                    continue
                try:
                    n = int(line)
                    ok = True
                except ValueError as e:
                    print(
                        f"Warning: skipping line {self._ln} in {self.filename}, that cannot be parsed as integer"
                    )
            return n
        except StopIteration:
            self._file.close()
            raise StopIteration


class InMemoryTrace:
    """Reads a trace from a trace file and stores in memory the list of integers.
    The resulting object can be iterated upon, just like with LazyTrace"""

    def __init__(self, filename):
        self.filename = filename
        self.trace = list(LazyTrace(filename))

    def __iter__(self):
        return iter(self.trace)
