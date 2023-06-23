from zgw_consumers.concurrent import parallel


class mock_parallel(parallel):
    def map(self, fn, *iterables, timeout=None, chunksize=1):
        return map(fn, *iterables)
