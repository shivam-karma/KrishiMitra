import os
import sys
from model import predict_disease_and_generate_gradcam, model

# Print model structure
if model:
    print("Model Layers:")
    for layer in reversed(model.layers):
        print(f"Layer: {layer.name}, Type: {type(layer)}")
        if hasattr(layer, 'layers'):
            print("  Nested Layers:")
            for sub_layer in reversed(layer.layers):
                print(f"    SubLayer: {sub_layer.name}, Type: {type(sub_layer)}")

# Create a dummy image
import numpy as np
import cv2
dummy_img = np.zeros((128, 128, 3), dtype=np.uint8)
cv2.imwrite("dummy_test.jpg", dummy_img)

class_name, heatmap_path, confidence = predict_disease_and_generate_gradcam("dummy_test.jpg")
print(f"Class: {class_name}")
print(f"Heatmap path: {heatmap_path}")
print(f"Confidence: {confidence}")
print(f"Confidence: {confidence}")
