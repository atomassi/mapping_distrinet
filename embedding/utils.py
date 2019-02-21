import time

def timeit(f):
    def timed(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        end = time.time()
        return end - start, result

    return timed