"""Smallest useful Kubeflow Pipeline (KFP v2 SDK): two steps, one feeds the other.

    add(a, b) -> result ---> show(result)

Each @dsl.component becomes its own container/Pod when run on the cluster.
"""
from kfp import dsl, compiler


# STEP 1: a "component" = a normal Python function that runs in its own container.
# Type hints are REQUIRED: KFP uses them to wire inputs/outputs between steps.
@dsl.component(base_image="python:3.12-slim")
def add(a: int, b: int) -> int:
    return a + b


# STEP 2: receives the output of step 1.
@dsl.component(base_image="python:3.12-slim")
def show(result: int):
    print(f"The result is {result}")


# PIPELINE: only describes the graph (what runs, in what order).
# Passing add_task.output into show() is what creates the dependency.
@dsl.pipeline(name="add-and-show")
def my_pipeline(a: int = 1, b: int = 2):
    add_task = add(a=a, b=b)
    show(result=add_task.output)


if __name__ == "__main__":
    # Compile to YAML, which you upload in the Kubeflow Pipelines UI
    # (or submit with kfp.Client, see README).
    compiler.Compiler().compile(my_pipeline, "pipeline.yaml")
    print("Wrote pipeline.yaml")
