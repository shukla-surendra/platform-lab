from transformers import ViTImageProcessor, FlaxViTModel
from PIL import Image
import requests

url = "http://images.cocodataset.org/val2017/000000039769.jpg"
image = Image.open(requests.get(url, stream=True).raw)

processor = ViTImageProcessor.from_pretrained("google/vit-base-patch16-224-in21k")
model = FlaxViTModel.from_pretrained("google/vit-base-patch16-224-in21k")

inputs = processor(images=image, return_tensors="np")
outputs = model(**inputs)
last_hidden_states = outputs.last_hidden_state

print("input pixel_values shape:", inputs["pixel_values"].shape)
print("last_hidden_state shape:", last_hidden_states.shape)
assert last_hidden_states.shape == (1, 197, 768)
print("OK: FlaxViTModel forward pass works")
