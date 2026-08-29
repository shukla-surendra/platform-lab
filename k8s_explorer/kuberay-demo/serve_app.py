import ray
from ray import serve
from starlette.requests import Request

ray.init(address="auto")


@serve.deployment(num_replicas=2)
class SquareService:
    def __call__(self, request: Request):
        x = int(request.query_params.get("x", 0))
        return {"x": x, "square": x * x}


serve.start(http_options={"host": "0.0.0.0", "port": 8010})
serve.run(SquareService.bind(), name="square-service", route_prefix="/square")
print("deployed: http://localhost:8010/square?x=7")
