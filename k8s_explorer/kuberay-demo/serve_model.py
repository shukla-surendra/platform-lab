"""
Real Ray Serve deployment: serves live predictions from the model
`train_job.py` trained and saved to model.joblib.

Run train_job.py first (via `ray job submit`, see its docstring), then:

    python serve_model.py

Then send a real feature vector:

    curl -X POST http://localhost:8010/predict \\
      -H "Content-Type: application/json" \\
      -d '{"features": [17.99, 10.38, 122.8, 1001, 0.1184, 0.2776, 0.3001, \\
                        0.1471, 0.2419, 0.0787, 1.095, 0.9053, 8.589, 153.4, \\
                        0.0064, 0.049, 0.0537, 0.0159, 0.03, 0.0062, 25.38, \\
                        17.33, 184.6, 2019, 0.1622, 0.6656, 0.7119, 0.2654, \\
                        0.4601, 0.1189]}'
"""

from pathlib import Path

import joblib
import ray
from ray import serve
from starlette.requests import Request

ARTIFACT_PATH = Path(__file__).parent / "model.joblib"

ray.init(address="auto")


@serve.deployment(num_replicas=2)
class BreastCancerClassifier:
    def __init__(self):
        artifact = joblib.load(ARTIFACT_PATH)
        self.model = artifact["model"]
        self.target_names = artifact["target_names"]
        self.feature_names = artifact["feature_names"]
        self.test_accuracy = artifact["test_accuracy"]

    async def __call__(self, request: Request):
        body = await request.json()
        features = body.get("features")

        if features is None or len(features) != len(self.feature_names):
            return {
                "error": f"expected 'features' as a list of {len(self.feature_names)} floats",
                "feature_names": self.feature_names,
            }

        prediction = self.model.predict([features])[0]
        probabilities = self.model.predict_proba([features])[0]

        return {
            "prediction": self.target_names[prediction],
            "probabilities": {
                self.target_names[i]: round(float(p), 4)
                for i, p in enumerate(probabilities)
            },
            "model_test_accuracy": round(self.test_accuracy, 4),
        }


serve.start(http_options={"host": "0.0.0.0", "port": 8010})
serve.run(
    BreastCancerClassifier.bind(),
    name="breast-cancer-classifier",
    route_prefix="/predict",
)
print("deployed: POST http://localhost:8010/predict")
