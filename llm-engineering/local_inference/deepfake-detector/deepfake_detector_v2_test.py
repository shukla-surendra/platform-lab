import sys

import requests
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

# Default is just a smoke-test image (not a face) to confirm the pipeline runs.
# Pass a real path or URL to a face image as argv[1] to get a meaningful prediction:
#   uv run python deepfake-detector/deepfake_detector_v2_test.py path/or/url/to/face.jpg
DEFAULT_IMAGE_URL = "http://images.cocodataset.org/val2017/000000039769.jpg"


def load_image(source: str) -> Image.Image:
    if source.startswith("http://") or source.startswith("https://"):
        return Image.open(requests.get(source, stream=True).raw).convert("RGB")
    return Image.open(source).convert("RGB")


image_source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE_URL
image = load_image(image_source)

processor = AutoImageProcessor.from_pretrained("prithivMLmods/Deep-Fake-Detector-v2-Model")
model = AutoModelForImageClassification.from_pretrained("prithivMLmods/Deep-Fake-Detector-v2-Model")
model.eval()

inputs = processor(images=image, return_tensors="pt")
with torch.no_grad():
    logits = model(**inputs).logits
    probs = torch.nn.functional.softmax(logits, dim=-1)[0]

id2label = model.config.id2label
for idx, prob in enumerate(probs):
    print(f"{id2label[idx]}: {prob.item():.4f}")

predicted = id2label[probs.argmax().item()]
print(f"\nPredicted: {predicted}")
