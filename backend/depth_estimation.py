import cv2
from PIL import Image
import io
import sys
import os
import base64
import traceback
import base64
import numpy as np
import torch
import tempfile
import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import sys

# Add path to 'ml-depth-pro/src'
current_dir = os.path.dirname(os.path.abspath(__file__))  # path to backend/
depth_module_path = os.path.join(current_dir, "ml-depth-pro", "src")
sys.path.append(depth_module_path)
import depth_pro

depth_model, transform = depth_pro.create_model_and_transforms()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
depth_model = depth_model.to(device)
depth_model.eval()


def classify_dent_severity(depth_m):
    if depth_m <= 0.010:
        return "Minor", "Very shallow dent, cosmetic only"
    elif depth_m <= 0.050:
        return "Moderate", "Noticeable dent, may need repair/filler"
    elif depth_m < 0.100:
        return "Severe", "Deep dent affecting panel shape"
    else:
        return "Critical", "Very deep dent; may require panel replacement"

def process_dent_depth_and_severity(
    original_img: np.ndarray,
    detections: list,
    dent_class_id: int,
    depth_model,
    transform,
    device
):
    # Filter only dent detections
    dent_detections = [det for det in detections if det["class"].lower() == "dent"]

    if not dent_detections:
        return {
            "message": "No dent detected in the image."
        }

    # Find largest dent box by area
    largest_dent = max(dent_detections, key=lambda d: (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]))
    x1, y1, x2, y2 = map(int, largest_dent["bbox"])
    cropped_url = largest_dent.get("image_url", "")

    # Convert image to tensor for depth estimation
    _, img_encoded = cv2.imencode('.jpg', original_img)
    pil_img = Image.open(io.BytesIO(img_encoded.tobytes())).convert("RGB")
    input_tensor = transform(pil_img).unsqueeze(0).to(device)

    with torch.no_grad():
        prediction = depth_model.infer(input_tensor)

    depth_map = prediction["depth"].squeeze().cpu().numpy()
    height, width = depth_map.shape

    # Clip to ensure coordinates are valid
    x1 = np.clip(x1, 0, width - 1)
    x2 = np.clip(x2, 0, width - 1)
    y1 = np.clip(y1, 0, height - 1)
    y2 = np.clip(y2, 0, height - 1)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

    # Depth analysis
    center_depth = depth_map[cy, cx]
    corners = [depth_map[y1, x1], depth_map[y1, x2], depth_map[y2, x1], depth_map[y2, x2]]
    avg_corner_depth = sum(corners) / 4.0
    dent_depth = round(abs(center_depth - avg_corner_depth), 4)

    severity_label, meaning = classify_dent_severity(dent_depth)

    # Annotate and upload image
    annotated_img = original_img.copy()
    cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
    # cv2.putText(annotated_img, f"{severity_la{dent_depth:.4f}m", (x1, y1 - 10),
    #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    _, img_annotated_encoded = cv2.imencode('.jpg', annotated_img)
    img_bytes_io = io.BytesIO(img_annotated_encoded.tobytes())
    upload_result = cloudinary.uploader.upload(img_bytes_io, resource_type="image")
    annotated_url = upload_result["secure_url"]

    return {
        "dent_bbox": [x1, y1, x2, y2],
        "dent_depth_m": f"{str(dent_depth)}m",
        "severity_label": severity_label,
        "severity_meaning": meaning,
        "cropped_url": cropped_url,
        "annotated_url": annotated_url,
        "confidence": largest_dent.get("confidence", None)
    }



