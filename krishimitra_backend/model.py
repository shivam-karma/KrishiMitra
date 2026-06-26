import os
import sys
import numpy as np
import cv2

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "saved_model")  # TF SavedModel directory
IMG_SIZE   = 128  # Must match training: model expects (128, 128, 3), NOT 224

# ── Classes must match alphabetical folder order from training ────────────────
# Keras ImageDataGenerator sorts: Healthy=0, Leaf_Spot=1, Rust=2
CLASS_NAMES = ['Healthy', 'Leaf_Spot', 'Rust']

DISEASES = {
    "Healthy": {
        "why_it_happens": "Plant is receiving optimal care, sunlight, and nutrients.",
        "spread_details": "N/A - plant is disease-free.",
        "treatment": "None required.",
        "steps_to_cure": ["Continue current watering schedule", "Monitor for early signs of pests"]
    },
    "Leaf_Spot": {
        "why_it_happens": "Usually caused by fungal/bacterial pathogens thriving in wet, warm conditions.",
        "spread_details": "Spores spread rapidly via wind, splashing rain, or contaminated tools.",
        "treatment": "Fungicide application and removal of infected leaves.",
        "steps_to_cure": [
            "Remove and destroy infected leaves",
            "Apply copper-based fungicide",
            "Avoid overhead watering"
        ]
    },
    "Rust": {
        "why_it_happens": "Fungal disease from the order Pucciniales that attacks leaves.",
        "spread_details": "Wind-borne spores can travel long distances to infect other plants.",
        "treatment": "Sulfur-based pesticides and improving air circulation.",
        "steps_to_cure": [
            "Apply sulfur fungicide",
            "Prune dense foliage",
            "Clean up fallen debris"
        ]
    },
}

# ── Load model ───────────────────────────────────────────────────────────────
model = None
if TF_AVAILABLE:
    try:
        model = tf.keras.models.load_model(MODEL_PATH)
        print(f"Model loaded OK: {MODEL_PATH}")
        print(f"  Output shape: {model.output_shape}")
    except Exception as e:
        print(f"WARNING: Could not load model. Error: {e}")
        model = None
else:
    print("WARNING: TensorFlow not installed (likely due to free tier disk limits).")

# ── Preprocessing to match EfficientNetB0 training ───────────────────────────

def _preprocess(img_rgb_uint8):
    """Rescale to [0,1] matching training rescale=1./255. Input must be (128,128,3)."""
    x = img_rgb_uint8.astype(np.float32) / 255.0
    return np.expand_dims(x, axis=0)  # shape: (1, 128, 128, 3)

# ── Public helpers ────────────────────────────────────────────────────────────
def get_disease_info(class_name: str) -> dict:
    return DISEASES.get(class_name, DISEASES['Leaf_Spot'])

def make_gradcam_heatmap(img_array, grad_model, pred_index):
    with tf.GradientTape() as tape:
        last_conv_output, preds = grad_model(img_array)
        class_channel = preds[:, pred_index]

    grads = tape.gradient(class_channel, last_conv_output)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    last_conv_output = last_conv_output[0]
    heatmap = last_conv_output @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0) / (tf.math.reduce_max(heatmap) + 1e-8)
    return heatmap.numpy()

def predict_disease_and_generate_gradcam(image_path: str):
    """
    Returns:
        (class_name: str, heatmap_path: str, confidence: float)
    On failure returns ('Healthy', '', 0.0).
    """
    if not TF_AVAILABLE or model is None:
        print("TensorFlow/Model not loaded - returning mock result to save server space.")
        return 'Healthy', '', 0.0

    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        print(f"Could not read image: {image_path}")
        return 'Healthy', '', 0.0

    try:
        # Pre-process (must match training preprocessing)
        img_rgb     = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (IMG_SIZE, IMG_SIZE))
        img_array   = _preprocess(img_resized)  # (1,128,128,3)

        # Predict
        preds      = model.predict(img_array)  # (1, 3)
        pred_index = int(np.argmax(preds[0]))
        confidence = float(np.max(preds[0]))
        class_name = CLASS_NAMES[pred_index] if pred_index < len(CLASS_NAMES) else 'Healthy'

        print(f"Prediction: {class_name} ({confidence*100:.1f}%)")

        # Find the last convolutional layer for Grad-CAM
        last_conv_layer_node = None
        for layer in reversed(model.layers):
            # Check if the layer itself is a Conv2D layer (for flat models)
            if isinstance(layer, tf.keras.layers.Conv2D):
                last_conv_layer_node = layer
                break
            # Check if it's a nested base model (for transfer learning models)
            if hasattr(layer, 'layers'):
                for sub_layer in reversed(layer.layers):
                    if isinstance(sub_layer, tf.keras.layers.Conv2D) or 'conv' in sub_layer.name.lower():
                        last_conv_layer_node = sub_layer
                        break
            if last_conv_layer_node: 
                break

        heatmap_path = ""
        if last_conv_layer_node:
            try:
                # Build specific Grad-CAM model
                grad_model = tf.keras.Model(
                    inputs=model.inputs,
                    outputs=[last_conv_layer_node.output, model.output]
                )
                heatmap = make_gradcam_heatmap(img_array, grad_model, pred_index)

                h, w = img_bgr.shape[:2]
                heatmap_resized = cv2.resize(heatmap, (w, h))
                heatmap_uint8   = np.uint8(255 * heatmap_resized)
                heatmap_color   = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
                superimposed    = cv2.addWeighted(img_bgr, 0.6, heatmap_color, 0.4, 0)

                base, ext = os.path.splitext(image_path)
                heatmap_path = f"{base}_heatmap{ext or '.jpg'}"
                cv2.imwrite(heatmap_path, superimposed)
            except Exception as grad_err:
                print(f"Grad-CAM failed (non-fatal): {grad_err}")

        return class_name, heatmap_path, confidence

    except Exception as e:
        print(f"Prediction failed: {e}")
        return 'Healthy', '', 0.0
