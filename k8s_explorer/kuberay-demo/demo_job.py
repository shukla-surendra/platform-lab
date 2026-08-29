import time

import ray

ray.init(address="auto")


@ray.remote
def slow_square(x):
    time.sleep(1)
    return x * x


futures = [slow_square.remote(x) for x in range(8)]
results = ray.get(futures)
print("results:", results)
print("nodes:", len(ray.nodes()))
