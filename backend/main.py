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
from pydantic import BaseModel
import cloudinary.api
import ultralytics
import uvicorn
import uuid
from googleapiclient.errors import HttpError
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from ultralytics import YOLO
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import nest_asyncio
from depth_estimation import process_dent_depth_and_severity
import math
from torchvision import transforms, models
import json
import base64
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from serpapi import GoogleSearch
from bs4 import BeautifulSoup
import re
import requests
import json
from urllib.parse import urlparse
from google.oauth2 import service_account
from googleapiclient.discovery import build
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from openpyxl import Workbook
import gspread
from google.oauth2.service_account import Credentials
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import JSONResponse
import os, uuid, json
from fastapi import Body
from depth_estimation import depth_model, transform
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), 'ml-depth-pro'))
sys.path.append('/backend/ml-depth-pro/src')

# Apply Colab patch
nest_asyncio.apply()

# Initialize FastAPI app
app = FastAPI(
    title="VDIP - Vehicle Damage Intelligence Platform",
    description="AI-driven vehicle damage detection, severity assessment, and repair/replace decisioning.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Load YOLO and depth model only once
from ultralytics import YOLO
yolo_model = YOLO(r"weights/20epochyolov8s.pt")
rust_detection_model=YOLO(r"weights/rust_detection_model.pt")
rust_model = r"weights/resnet18_rust_severity_folderdata.pt"

general_class_names = ['dent', 'scratch', 'crack', 'glass shatter', 'lamp broken']
rust_class_names = ["rust"]
dent_class_id = general_class_names.index('dent')


cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


def detect_all_damages(img: np.ndarray, general_model, general_class_names: list,
                       rust_model, rust_class_names: list, selected_damage_type: str = None):
    import numpy as np
    import cv2
    import io
    import cloudinary.uploader
    from collections import defaultdict

    annotated_image = img.copy()
    all_detections = []
    if isinstance(img, list):
        img = img[0]
    # --------- General Damage Detection ---------
    results_general = general_model(img)
    for box in results_general[0].boxes:
        class_id = int(box.cls[0].item())
        if class_id >= len(general_class_names):
            print(f"[⚠️ Warning] Detected invalid class_id: {class_id}. Skipping...")
            continue

        class_name = general_class_names[class_id]
        if selected_damage_type and class_name.lower() != selected_damage_type.lower():
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0].item())

        crop = img[max(0, y1 - 10):y2 + 10, max(0, x1 - 10):x2 + 10]
        cv2.putText(crop, f"{class_name} ({conf:.2f})", (5, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        _, cropped_encoded = cv2.imencode('.jpg', crop)
        cropped_bytes_io = io.BytesIO(cropped_encoded.tobytes())
        upload_result = cloudinary.uploader.upload(cropped_bytes_io, resource_type="image")
        cropped_url = upload_result["secure_url"]

        all_detections.append({
            "type": class_name,
            "confidence": round(conf, 4),
            "bbox": [x1, y1, x2, y2],
            "image_url": cropped_url
        })

    # --------- Rust Detection ---------
    results_rust = rust_detection_model(img)
    for box in results_rust[0].boxes:
        class_id = int(box.cls[0].item())
        if class_id >= len(rust_class_names):
            continue

        class_name = rust_class_names[class_id]
        if selected_damage_type and class_name.lower() != selected_damage_type.lower():
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0].item())

        crop = img[max(0, y1 - 10):y2 + 10, max(0, x1 - 10):x2 + 10]
        cv2.putText(crop, f"{class_name} ({conf:.2f})", (5, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        _, cropped_encoded = cv2.imencode('.jpg', crop)
        cropped_bytes_io = io.BytesIO(cropped_encoded.tobytes())
        upload_result = cloudinary.uploader.upload(cropped_bytes_io, resource_type="image")
        cropped_url = upload_result["secure_url"]

        all_detections.append({
            "type": class_name,
            "confidence": round(conf, 4),
            "bbox": [x1, y1, x2, y2],
            "image_url": cropped_url
        })

    # --------- Draw Only Largest BBox(es) ---------
    grouped = defaultdict(list)
    for det in all_detections:
        grouped[det["type"]].append(det)

    if selected_damage_type:
        dets = grouped.get(selected_damage_type, [])
        if dets:
            max_det = max(dets, key=lambda d: (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]))
            x1, y1, x2, y2 = max_det["bbox"]
            cv2.rectangle(annotated_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(annotated_image, f"{max_det['type']} ({max_det['confidence']:.2f})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    else:
        for damage_type, dets in grouped.items():
            max_det = max(dets, key=lambda d: (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]))
            x1, y1, x2, y2 = max_det["bbox"]
            cv2.rectangle(annotated_image, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(annotated_image, f"{max_det['type']} ({max_det['confidence']:.2f})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    return all_detections, annotated_image


def get_largest_bbox_per_type(detections):
    """
    From a list of detections, extract the largest bbox (as list of coordinates) for each damage type.
    """
    from collections import defaultdict

    grouped = defaultdict(list)

    # Group detections by type
    for det in detections:
        grouped[det['type']].append(det)

    largest_per_type = {}

    for damage_type, det_list in grouped.items():
        # Find detection with largest area
        max_det = max(
            det_list,
            key=lambda d: (d['bbox'][2] - d['bbox'][0]) * (d['bbox'][3] - d['bbox'][1])
        )
        largest_per_type[damage_type] = max_det['bbox']  # Only bbox as [x1, y1, x2, y2]

    return largest_per_type



def calculate_crack_length_and_severity(bboxes, pixel_to_cm=0.0264583333):
    """
    Calculate composite severity score from crack bounding boxes.
    Uses a weighted formula based on length, width, area, and aspect ratio.
    Returns the overall severity score and individual crack metrics.
    """
    total_area = 0
    weighted_severity_sum = 0
    crack_details = []

    for idx, (x1, y1, x2, y2) in enumerate(bboxes):
        x1, y1, x2, y2 = map(float, (x1, y1, x2, y2))
        width_px = abs(x2 - x1)
        height_px = abs(y2 - y1)

        width_cm = width_px * pixel_to_cm
        height_cm = height_px * pixel_to_cm

        length_cm = round(math.hypot(width_cm, height_cm), 2)
        area_cm2 = width_cm * height_cm
        aspect_ratio = round(length_cm / width_cm, 2) if width_cm != 0 else 0

        severity = (
            0.25 * length_cm +
            0.15 * width_cm +
            0.25 * area_cm2 +
            0.1 * aspect_ratio
        )

        weighted_severity_sum += severity * area_cm2
        total_area += area_cm2

        crack_details.append({
            "bbox": (x1, y1, x2, y2),
            "length_cm": length_cm,
            "width_cm": round(width_cm, 2),
            "area_cm2": round(area_cm2, 2),
            "aspect_ratio": aspect_ratio,
            "severity_component": round(severity, 2)
        })

    overall_severity = round(weighted_severity_sum / total_area, 2) if total_area else 0
    return overall_severity, length_cm


def classify_crack_severity(score):
    if score <= 5.0:
        return "Minor", "Short, narrow, superficial cracks"
    elif score <= 12.0:
        return "Moderate", "Long or wide cracks; medium surface damage"
    elif score <= 20.0:
        return "Severe", "Long and wide cracks — may need repainting"
    else:
        return "Critical", "Very large cracks or gashes — may indicate structural damage"



def calculate_scratch_length_and_severity(bboxes, pixel_to_cm=0.0264583333):
    """
    Calculate severity score for scratches based on bounding boxes.
    Uses a weighted formula involving length, width, area, and aspect ratio.
    """
    total_area = 0
    weighted_severity_sum = 0
    scratch_details = []


    for idx, (x1, y1, x2, y2) in enumerate(bboxes):
        x1, y1, x2, y2 = map(float, (x1, y1, x2, y2))
        width_px = abs(x2 - x1)
        height_px = abs(y2 - y1)

        width_cm = width_px * pixel_to_cm
        height_cm = height_px * pixel_to_cm

        length_cm = round(math.hypot(width_cm, height_cm), 2)
        area_cm2 = width_cm * height_cm
        aspect_ratio = round(length_cm / width_cm, 2) if width_cm != 0 else 0

        severity = (
            0.4 * length_cm +
            0.2 * width_cm +
            0.3 * area_cm2 +
            0.1 * aspect_ratio
        )

        weighted_severity_sum += severity * area_cm2
        total_area += area_cm2

        scratch_details.append({
            "bbox": (x1, y1, x2, y2),
            "length_cm": length_cm,
            "width_cm": round(width_cm, 2),
            "area_cm2": round(area_cm2, 2),
            "aspect_ratio": aspect_ratio,
            "severity_component": round(severity, 2)
        })

    overall_severity = round(weighted_severity_sum / total_area, 2) if total_area else 0
    return overall_severity, length_cm

def classify_scratch_severity(score):
    """
    Classify scratch severity level based on score.
    """
    if score <= 5.0:
        return "Minor", "Short, narrow, superficial scratches"
    elif score <= 10.0:
        return "Moderate", "Long or wide scratches; medium surface damage"
    elif score <= 20.0:
        return "Severe", "Long and wide scratches — may need repainting"
    else:
        return "Critical", "Very large scratches — may indicate structural damage"


def classify_rust_severity(img: np.ndarray, rust_bboxes: list):
    """
    Classifies the severity of rust for each rust bounding box.

    Args:
        img (np.ndarray): Original image in BGR format.
        rust_bboxes (list): List of bounding boxes in [x1, y1, x2, y2] format.

    Returns:
        List of dictionaries with keys: bbox, severity, confidence
    """
    results = []
    img_size = 224
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    class_names = ['Heavy Visible Rust','Slightly Visible Rust','Visible Rust']

    transform = transforms.Compose([
    transforms.Resize((224, 224)),  # Match model input size
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],  # ImageNet mean
                         std=[0.229, 0.224, 0.225])   # ImageNet std
])

    for i, bbox in enumerate(rust_bboxes):
        x1, y1, x2, y2 = bbox
        x1, y1, x2, y2 = max(x1, 0), max(y1, 0), min(x2, img.shape[1]), min(y2, img.shape[0])
        cropped = img[y1:y2, x1:x2]

        # Convert to PIL and apply transforms
        image_pil = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
        input_tensor = transform(image_pil).unsqueeze(0).to(device)


        model = models.resnet18(pretrained=False)
        model.fc = torch.nn.Linear(model.fc.in_features, len(class_names))
        model.load_state_dict(torch.load(rust_model, map_location=device))
        model.eval()
        model.to(device)

        with torch.no_grad():
            outputs = model(input_tensor)
            probs = torch.nn.functional.softmax(outputs[0], dim=0)
            predicted_class = torch.argmax(probs).item()

        # Rule-based adjustment
        if probs[class_names.index("Visible Rust")].item() > 0.85:
            predicted_class = class_names.index("Heavy Visible Rust")
        elif probs[class_names.index("Slightly Visible Rust")].item() > 0.40:
            predicted_class = class_names.index("Slightly Visible Rust")

        severity = class_names[predicted_class]
        confidence = round(probs[predicted_class].item(), 4)

        results.append({
            "bbox": [x1, y1, x2, y2],
            "severity": severity,
            "confidence": confidence
        })

    return results

def analyze_damage_function(image_path, damage_type=None):
    img = cv2.imread(image_path)
    if img is None:
        return {"error": "Failed to read image. Please check the path."}

    detections, annotated_image = detect_all_damages(
        img,
        general_model=yolo_model,
        general_class_names=general_class_names,
        rust_model=rust_model,
        rust_class_names=rust_class_names,
        selected_damage_type=damage_type
    )

    largest_detections = get_largest_bbox_per_type(detections)

    output_image = annotated_image.copy()
    results = []
    decisions = []
    image_modified = False

    # Define handlers
    damage_handlers = {
        "dent": lambda bbox: (
            lambda dent_result: {
                "depth": dent_result["dent_depth_m"],
                "severity": dent_result["severity_label"]
            }
        )(process_dent_depth_and_severity(
            detections=[{"bbox": bbox, "class": "dent"}],
            dent_class_id=dent_class_id,
            depth_model=depth_model,
            transform=transform,
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
            original_img=img
        )),
        "scratch": lambda bbox: {
            "length": f"{round(calculate_scratch_length_and_severity([bbox])[1], 2)}cm",
            "severity": classify_scratch_severity(calculate_scratch_length_and_severity([bbox])[0])[0]
        },
        "crack": lambda bbox: {
            "length": f"{round(calculate_crack_length_and_severity([bbox])[1], 2)}cm",
            "severity": classify_crack_severity(calculate_crack_length_and_severity([bbox])[0])[0]
        },
        "rust": lambda bbox: (
            lambda result: {
                "severity": result["severity"],
                "confidence": result["confidence"]
            }
        )(classify_rust_severity(img, [bbox])[0]),
        "glass shatter": None,
        "lamp broken": None
    }

    selected_types = [damage_type.lower()] if damage_type else list(damage_handlers.keys())

    for dtype in selected_types:
        if dtype not in damage_handlers:
            results.append({
                "class": dtype,
                "error": f"'{dtype}' is not a supported damage type."
            })
            continue

        if dtype in ["dent", "scratch", "crack", "rust"]:
            if dtype not in largest_detections:
                results.append({
                    "class": dtype,
                    "message": f"{dtype} not detected in the image."
                })
                continue

            bbox = largest_detections[dtype]
            x1, y1, x2, y2 = bbox
            processed = damage_handlers[dtype](bbox)

            # Get severity (if available)
            severity = processed.get("severity")
            decision = defect_reasoning_agent(dtype, severity)

            # Annotate image
            label_text = f"{dtype} ({severity})" if severity else dtype
            cv2.rectangle(output_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(output_image, label_text, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            image_modified = True

            result_entry = {
                "class": dtype,
                "bbox": [x1, y1, x2, y2],
                "severity": severity,
                "decision": decision
            }

            if "length" in processed:
                result_entry["length"] = processed["length"]
            if "depth" in processed:
                result_entry["depth"] = processed["depth"]
            if "confidence" in processed:
                result_entry["confidence"] = processed["confidence"]

            results.append(result_entry)
            decisions.append({ "class": dtype, "decision": decision })

        elif dtype in ["glass shatter", "lamp broken"]:
            if dtype not in largest_detections:
                results.append({
                    "class": dtype,
                    "message": f"{dtype} not detected in the image."
                })
                continue

            bbox = largest_detections[dtype]
            x1, y1, x2, y2 = bbox
            decision = defect_reasoning_agent(dtype, None)

            cv2.rectangle(output_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            image_modified = True

            result_entry = {
                "class": dtype,
                "bbox": [x1, y1, x2, y2],
                "decision": decision
            }

            results.append(result_entry)
            decisions.append({ "class": dtype, "decision": decision })

    # Save and upload final image only once
    final_image_url = None
    if image_modified:
        os.makedirs("output_images", exist_ok=True)
        final_img_name = f"output_{uuid.uuid4().hex}.jpg"
        output_path = os.path.join("output_images", final_img_name)
        cv2.imwrite(output_path, output_image)
        final_image_url = upload_to_cloudinary(output_path)

    return {
        "results": results,
        "decisions": decisions,
        "final_image": final_image_url or "No annotated image generated"
    }

def defect_reasoning_agent(defect_type, severity=None):
    defect_type = defect_type.lower()

    if defect_type in ['glass shutter', 'lamp broken']:
        return 'Replace'

    if defect_type in ['crack', 'scratch']:
        if severity in ['Minor', 'Moderate']:
            return 'Repair'
        elif severity in ['Severe', 'Critical']:
            return 'Replace'
        else:
            return 'Replace'

    elif defect_type == 'dent':
        if severity in ['Minor', 'Moderate']:
            return 'Repair'
        elif severity in ['Severe', 'Critical']:
            return 'Replace'
        else:
            return 'Replace'

    elif defect_type == 'rust':
        if severity == 'Slightly Visible Rust':
            return 'Repair'
        elif severity in ['Visible Rust', 'Heavy Visible Rust']:
            return 'Replace'
        else:
            return 'Replace'

    else:
        return 'Replace'


def upload_to_cloudinary(local_path):
    response = cloudinary.uploader.upload(local_path)
    return response["secure_url"]

####################### Agent Graph Definition #######################

EXCEL_FILE = "vehicle_damage_report.xlsx"
 
class State(TypedDict):
    response_json_json: str
    image_path: str
    output: Dict[str, Any]
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["GOOGLE_GEMINI_MODEL"] = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.0-flash")
 
 
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.environ["GOOGLE_API_KEY"]
)
def scrape_prices_from_links(links):
    prices = []
    for url in links:
        try:
            resp = requests.get(
                url,
                timeout=20,  # ⏳ 10 second timeout
                headers={"User-Agent": "Mozilla/5.0"}
            )
            resp.raise_for_status()  # Will throw for HTTP errors
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(" ", strip=True)
 
            found_prices = re.findall(r"[$₹€]\s?\d{1,3}(?:[,\d{3}]*)(?:\.\d{1,2})?", text)
            print(found_prices)
 
            for p in found_prices:
                p_clean = re.sub(r"[^\d.]", "", p)
                try:
                    prices.append(float(p_clean))
                except ValueError:
                    continue
 
        except requests.exceptions.Timeout:
            print(f"⏳ Timeout while scraping: {url}")
            continue
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request error scraping {url}: {e}")
            continue
        except Exception as e:
            print(f"⚠️ Unexpected error scraping {url}: {e}")
            continue
 
    return prices
 
def estimate_price_range_with_gemini(prices):
    if not prices:
        return "No prices found."
    prices_str = ", ".join(map(str, prices))
    print(prices_str)
    messages = [
        SystemMessage(content="You are an expert at summarizing market prices for vehicle parts."),
        HumanMessage(content=f"""
Here is a list of observed prices for a vehicle replacement part: {prices_str}.
 
Analyze them and return only an estimated realistic market range in the format:
$min_price - $max_price
Do not add explanations.
""")
    ]
    return llm.invoke(messages).content.strip()
 
def price_estimator_node(state: State):
    output = state.get("output", {})
    for part, details in output.items():
        if details.get("replacement_links"):
            prices = scrape_prices_from_links(details["replacement_links"])
            details["estimated_price_range"] = estimate_price_range_with_gemini(prices)
        else:
            details["estimated_price_range"] = ""
    state["output"] = output
    return state
 
def encode_image_base64(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        img_bytes = img_file.read()
    encoded = base64.b64encode(img_bytes).decode("utf-8")
    ext = image_path.split(".")[-1].lower()
    mime_type = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
    return f"data:{mime_type};base64,{encoded}"
 
# =========================
# TOOL: REPAIR GUIDE
# =========================
def repair_methodology_tool(input_str: str, image_path: str) -> str:
    image_data_url = encode_image_base64(image_path)
    messages = [
            SystemMessage(
                content="You are a master auto repair technician helping beginners fix vehicle damage based on images and descriptions."
            ),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": f"""
The damage type is: "{input_str}".
From the provided image, first identify the **specific part of the car** that is damaged.
 
Then write a highly descriptive  repair guide for a beginner using this format:
 
1. Identified Part Name
2. Tools & Safety Gear (bulleted list)
3. Estimated Time
4. Estimated Price in Dollars
5. Step-by-Step Repair Instructions (if damage is minor or moderate) (only 5 steps)
6. Safety Tips (brief list)
 
Always:
- Use beginner-friendly language.
- Emphasize safety.
- Avoid jargon or explain it clearly.
"""
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_data_url
                    }
                }
            ])
        ]
    return llm.invoke(messages).content
 
# =========================
# TOOL: GENERATE SEARCH QUERY
# =========================
def generate_search_query_from_damage(damage_description: str, image_path: str) -> str:
    """
    This function uses Gemini to:
    1. Identify the specific damaged car part from image and description.
    2. Generate a Google Shopping query for finding replacement parts.
    """
    try:
        print("🔎 Calling Gemini to generate a robust shopping search query...")
        image_data_url = encode_image_base64(image_path)
 
        messages = [
            SystemMessage(
                content="You are a car parts identification and product search expert. Your job is to generate accurate, simple search queries for damaged car parts."
            ),
            HumanMessage(content=[
               {
  "type": "text",
  "text": """
You are a smart assistant trained to generate **Google Shopping search queries** with **high commercial intent**, specifically targeting **vehicle replacement parts**.
 
Your goal is to help users locate pages where they can **immediately view and compare product listings** for damaged car parts.
 
---
 
🔍 **Step 1: Identify the Damaged Part Precisely**
Analyze the vehicle damage description and identify the **exact part** and its **location**, such as:
- rear bumper
- right headlight
- front windshield
- left fog lamp
 
Focus on the **specific replaceable component**.
 
---
 
🔎 **Step 2: Generate a Google Shopping Query for Direct Product Results**
Craft a query **optimized to return product tiles on Google Shopping**, ensuring it targets **e-commerce listings** with strong commercial signals.
 
✅ Follow this format:
- Enclose every keyword in **double quotes**
- Use **`+`** to join each token: `"term1" + "term2" + ..."`
- Include:
  - Part name and location (e.g., "rear" + "bumper")
  - High-intent product keywords (e.g., "auto" + "replacement" + "parts")
  - Words commonly used in **shopping feeds or titles** (e.g., "vehicle", "spare", "OEM", "assembly")
- Keep the query concise: **7–12 tokens**
- Make it **suitable for Google Shopping**, so it surfaces **rich product listings**, not articles
 
 
 
🛒 **Final Output Format**
Respond with only **one single line**, exactly like this:
`Query: "term1" + "term2" + "term3" + ...`
 
Do not add explanation or formatting — just the line.
 
---
 
💡 **Example Input:**
Damage: broken rear tail light
 
💡 **Example Output:**
`Query: "rear" + "tail" + "light" + "car" + "replacement" + "spare" + "parts" + "vehicle"`
 
Begin now.
"""
}
 
 
 
,
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_data_url
                    }
                }
            ])
        ]
 
        result = llm.invoke(messages)
        return result.content.strip().replace("Query:", "").strip()
 
    except Exception as e:
        return f"⚠️ Error generating search query: {e}"
# =========================
# TOOL: SEARCH GOOGLE SHOPPING (SERPAPI)
# =========================
def search_google_shopping(query: str, api_key: str, cse_id: str, max_results=5):
    url = "https://www.googleapis.com/customsearch/v1"
 
    # No site filtering applied
    full_query = query  # Use the query as-is
 
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": full_query,
        "num": max_results
    }
 
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        links = [item["link"] for item in data.get("items", [])]
        return links if links else ["No results found."]
    else:
        return [f"⚠️ Error {response.status_code}: {response.text}"]
 
# =========================
# TOOL: HANDLE DAMAGE RESPONSE
# =========================
@tool(description="Process damage detection JSON and decide repair or replace, returning a structured guide and query results.")
def handle_damage_response(response_json_json: str, image_path: str) -> dict:
    response_json = json.loads(response_json_json)
    output_dict = {}
 
    for item in response_json.get("results", []):
        dtype = (item.get("class") or "").lower()
        severity = (item.get("severity") or "").lower()
        decision = (item.get("decision") or "").lower()
 
        if not dtype or not decision:
            continue
 
        entry = {
            "severity": severity or "unknown",
            "decision": decision or "unknown",
            "gemini_query": None,
            "replacement_links": [],
            "repair_guide": None,
        }
 
        full_description = f"{severity} {dtype}"
        if decision == "repair":
            entry["repair_guide"] = repair_methodology_tool(full_description, image_path)
        elif decision == "replace":
            raw_query = generate_search_query_from_damage(full_description, image_path)
            query = next((line.strip("* ").strip() for line in raw_query.split("\n") if line.strip()), raw_query)
            entry["gemini_query"] = query
            entry["replacement_links"] = search_google_shopping(query, os.getenv("GOOGLE_SEARCH_API_KEY"), os.getenv("GOOGLE_CSE_ID"))
 
        output_dict[dtype] = entry
 
    return output_dict

def extract_repair_cost_from_guide(guide_text: str) -> str:
    """
    Extract a price range like "$50-$100" or "$50 - $100" from the given text.
    Returns the first match found or empty string if none.
    """
    if not guide_text:
        return ""
 
    # Regex pattern explanation:
    # \$\d+(\.\d+)?  => matches dollar amount like $50 or $50.99
    # \s*[-–]\s*     => matches a dash (- or –) with optional spaces around
    # \$\d+(\.\d+)?  => matches second dollar amount like $100 or $100.50
    pattern = r"\$\d+(?:\.\d+)?\s*[-–]\s*\$\d+(?:\.\d+)?"
 
    match = re.search(pattern, guide_text)
    if match:
        return match.group(0).replace(" ", "")  # remove spaces in between, optional
    return ""
 
SERVICE_ACCOUNT_FILE = "new-auth-614e9-52407089bf00.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

 
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
 


#client = gspread.authorize(credentials)

sheet_service = build('sheets', 'v4', credentials=credentials)
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
 
def setup_headers():
    headers = [["Image", "result", "decision", "replace", "repair",
                "repair cost estimated", "replace cost estimated"]]
    sheet_service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1!A1:G1",
        valueInputOption="RAW",
        body={"values": headers}
    ).execute()
    print("Headers set successfully.")
 
def _label_from_url(url):
    try:
        p = urlparse(url)
        host = p.netloc.replace("www.", "")
        last_seg = os.path.basename(p.path)
        if last_seg and "." not in last_seg:
            return last_seg
        return host
    except Exception:
        return url
 
def _make_hyperlink(url):
    label = _label_from_url(url).replace('"', '')
    return f'HYPERLINK("{url}","{label}")'
 
def _join_links_formula(links):
    if not links:
        return ""
    parts = [_make_hyperlink(u) for u in links]
    return '=' + ' & CHAR(10) & '.join(parts) if len(parts) > 1 else '=' + parts[0]

def sanitize_title(title: str) -> str:
    """Google Sheets tab names cannot contain some special chars, so sanitize."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', title)[:90]  # max length 100 chars


def google_sheets_write_node(state: State, config, **kwargs) -> State:
    output = state.get("output", {})
    user_email = state.get("email_id", "guest")
 
    # Extract sheet name from email prefix
        # Extract sheet name from email prefix
    email = config.get("configurable", {}).get("email_name", user_email)
    sheet_name = email.split("@")[0] if email else "guest"
 
    state["sheet_name"] = sheet_name
    print("📄 Target sheet name:", sheet_name)
 
    # Get existing sheets
    existing_sheets = sheet_service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID
    ).execute()
    sheet_titles = [s['properties']['title'] for s in existing_sheets['sheets']]
 
    # Create new sheet/tab if missing
    if sheet_name not in sheet_titles:
        sheet_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
        ).execute()
        print(f"✅ Created new sheet/tab: {sheet_name}")
 
        # Re-fetch after creating sheet to get its sheetId
        existing_sheets = sheet_service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID
        ).execute()
        sheet_id = next(
            s["properties"]["sheetId"]
            for s in existing_sheets["sheets"]
            if s["properties"]["title"] == sheet_name
        )
 
        # Add headers
        headers = [["Image", "Result", "Decision", "Replace Links",
                    "Repair Guide","Repair Tools", "Repair Cost", "Replace Cost"]]
        sheet_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A1:H1",
            valueInputOption="RAW",
            body={"values": headers}
        ).execute()
        print("✅ Headers written.")
 
        # Make headers bold
        sheet_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,
                                "endRowIndex": 1,   # only first row
                                "startColumnIndex": 0,
                                "endColumnIndex": 8 # A–G
                            },
                            "cell": {
                                "userEnteredFormat": {
                        "textFormat": {"bold": True}
                   
                                }
                            },
                            "fields": "userEnteredFormat.textFormat.bold",
                        }
                    }
                ]
            }
        ).execute()
        print("✅ Header bold formatting applied.")
 
    else:
        print(f"✅ Using existing sheet/tab: {sheet_name}")
 
 
    # Extract response data
    response_dict = state["response_json_json"]
    response_json = json.loads(response_dict)
    final_image_url = response_json.get("final_image", "")
    print(f"[DEBUG] final_image_url: {final_image_url}")
 
    # Build rows
    image_formula = f'=IMAGE("{final_image_url}")' if final_image_url else ""
    decision_map = {d["class"]: d["decision"] for d in [
        {"class": p, "decision": details.get("decision", "")}
        for p, details in output.items()
    ] if d["decision"]}
 
    replacement_links_by_class = {p: details.get("replacement_links", []) for p, details in output.items()}
    repair_guides_by_class = {p: details.get("repair_guide", "") for p, details in output.items()}
    repair_cost_estimates_by_class = {
        p: extract_repair_cost_from_guide(details.get("repair_guide", "")) for p, details in output.items()
    }
    replace_cost_estimates_by_class = {p: details.get("estimated_price_range", "") for p, details in output.items()}
 
    rows = []
    for part, details in output.items():
        decision = decision_map.get(part, "")
 
        extras = []
        print("ye detail h---->",details)
        if details.get("severity"):
            extras.append(details["severity"])
        if details.get("length"):
            extras.append(str(details["length"]))
        if details.get("confidence") is not None:
            extras.append(f"conf:{round(details['confidence'],4)}")
        result_str = f"{part} ({', '.join(extras)})" if extras else part
 
        replace_links_formula = _join_links_formula(
            replacement_links_by_class.get(part, [])
        ) if decision.lower() == "replace" else ""
 
        # Clean ** before writing
        repair_text = repair_guides_by_class.get(part, "") if decision.lower() == "repair" else ""
        repair_text = repair_text.replace("**", " ")
        sections = re.findall(r'(\d\..*?)(?=\n\s*\d\.|$)', repair_text, flags=re.DOTALL)
        sections = [s.strip() for s in sections]  # clean up whitespace
 
        # Example: extract specific sections
        identified_part = sections[0] if len(sections) > 0 else ""
        tools_list = sections[1] if len(sections) > 1 else ""
        step_by_step = sections[4] if len(sections) > 4 else ""  # Step-by-Step section is usually 5th
 
        # Optional: remove bullets (*) from tools
        tools_list = "\n".join([line.lstrip("* ").strip() for line in tools_list.splitlines() if line.strip()])
        repair_cost = repair_cost_estimates_by_class.get(part, "")
        replace_cost = replace_cost_estimates_by_class.get(part, "")
 
        rows.append([
            image_formula,
            result_str,
            f"{part}: {decision}" if decision else "",
            replace_links_formula,
            step_by_step,
            tools_list,
            repair_cost,
            replace_cost
        ])
 
    # Debug print
    print("=== Rows to be written ===")
    for r in rows:
        print(r)
    print("==========================")
 
    # Append to sheet
    if rows:
        sheet_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A:G",   # ✅ use sheet_name, not session_id
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows}
        ).execute()
        print(f"✅ Wrote {len(rows)} rows to '{sheet_name}' for {user_email}")
 
    return state
 
def setup_headers_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws = wb.active
        ws.title = "Report"
        ws.append(["Image", "Result", "Decision", "Replace Links", "Repair Guide", "Repair Cost", "Replace Cost"])
        wb.save(EXCEL_FILE)
        print("✅ Excel headers created")
 
# =========================
# NODE FUNCTION
# =========================
def call_agent(state: State):
    setup_headers_excel()
    result = handle_damage_response.invoke({
        "response_json_json": state.get("response_json_json", "{}"),
        "image_path": state.get("image_path", "")
    })
    state["output"] = result
    return state
 
 
write_to_sheets_node = google_sheets_write_node
 
# =========================
# GRAPH DEFINITION
# =========================

graph = StateGraph(State)
graph.add_node("agent_node", call_agent)
graph.add_node("price_estimator_node", price_estimator_node)
graph.add_node("write_to_sheets_node", write_to_sheets_node)
graph.set_entry_point("agent_node")
graph.add_edge("agent_node", "price_estimator_node")
graph.add_edge("price_estimator_node", "write_to_sheets_node")
graph.add_edge("write_to_sheets_node", END)


graph_image_path = "graph_visualization.png"
compiled_graph = graph.compile()
 
with open(graph_image_path, "wb") as f:
    f.write(compiled_graph.get_graph().draw_mermaid_png())
print(f"✅ Graph visualization saved to {graph_image_path}")

import json

def prepare_sample_input(result: dict, image_path: str) -> dict:
    """
    Prepares a standardized sample_input for the graph pipeline.
    Uses the decision values directly from the input results dict,
    without modifying or generating them.
    """
    results_with_decisions = []
    decisions_list = []

    for item in result.get("results", []):
        # Keep item as-is (assume "decision" already provided)
        cls = item.get("class", "")
        decision = item.get("decision")

        # Add to decisions list only if decision exists
        if decision:
            decisions_list.append({"class": cls, "decision": decision})

        results_with_decisions.append(item)

    # Build standardized sample_input
    sample_input = {
        "response_json_json": json.dumps({
            "results": results_with_decisions,
            "decisions": decisions_list,
            "final_image": result.get("final_image", "")
        }),
        "image_path": image_path,
        "final_image": result.get("final_image", "")
    }

    return sample_input


# --- Config ---
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.office365.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 587))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
EXCEL_FILE = "vehicle_damage_report.xlsx"
 
@app.post("/email")
async def send_email_endpoint(email: str = Body(..., embed=True)):
    try:
        # Extract receiver's name from email
        receiver_raw = email.split("@")[0]
        receiver_name = receiver_raw.replace(".", " ").replace("_", " ").title()

        # Subject & spreadsheet link
        subject = "Fund Request for Parts Replacement/Repair – Vehicle Damage Intelligence Platform (VDIP)"
        spreadsheet_link = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"

        # Body
        body = (
            f"Hi {receiver_name},\n\n"
            "Please find attached the sheet containing the identified parts requiring replacement or repair. "
            "These results are generated from our Vehicle Damage Intelligence Platform (VDIP) using our model’s detection "
            "capabilities and AI agents.\n\n"
            "Kindly review the details and initiate the process for raising the necessary funds at the earliest.\n\n"
            f"You can view it here: {spreadsheet_link}\n\n"
            "Best regards,\n"
            "AISF Team"
        )

        # Create email
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Send via SMTP
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, [email], msg.as_string())

        return {"message": f"Report sent to {email}"}

    except Exception as e:
        return {"error": f"Failed to send email: {str(e)}"}


 
def background_processing(result, filename, damage_type, session_id, email_name, model):
    try:
        # Prepare state for the graph
        sample_input = prepare_sample_input(result, filename)
 
        # Run the graph pipeline (heavy part)
        final_state = compiled_graph.invoke(
            sample_input,
            config={"configurable": {"sessionid": session_id, "email_name": email_name}}
        )
        print("=== Final State ===")
        print(final_state["output"])
 
        # Save session results
        os.makedirs("sessions", exist_ok=True)
        with open(f"sessions/{session_id}.json", "w") as f:
            json.dump(final_state, f, indent=2)
 
        print(f"✅ Background task finished for session {session_id}")
    except Exception as e:
        print(f"⚠️ Background task error for session {session_id}: {e}")

class AgentRequest(BaseModel):
    response_json_json: str  # JSON string
    image_path: str  
    
from fastapi import HTTPException

@app.post("/analyze-damage")
async def analyze_damage_api(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    damage_type: str = Form(None),
    session_id: str = Form(None),
    email_id: str = Form(None),
    model: str = Form(None),
):
    contents = await file.read()
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)

    sessionid = session_id
    email_name = email_id.split("@")[0]
    filename = os.path.join(temp_dir, f"{uuid.uuid4().hex}.jpg")

    with open(filename, "wb") as f:
        f.write(contents)

    print(f"📌 Session ID received: {session_id}")
    print(f"📌 Model selected: {model}")

    # Run the prediction
    result = analyze_damage_function(filename, damage_type)
    print(f"Initial analysis result: {result}")

    # 🚨 ERROR HANDLING — NO ANNOTATED IMAGE
    if result.get("final_image") == "No annotated image generated":
        raise HTTPException(
            status_code=205,
            detail="No annotated image found. Detection failed. Please upload a clearer vehicle image."
        )

    all_classes = ['dent', 'scratch', 'crack', 'rust', 'glass shatter', 'lamp broken']

    formatted_results = {}
    for cls in all_classes:
        normalized_cls = cls.replace(" ", "_")
        item = next((x for x in result['results'] if x['class'] == cls), None)

        if item and any(k in item for k in ('bbox', 'severity', 'decision', 'length', 'depth')):
            base = {
                'bbox': item.get('bbox'),
                'severity': item.get('severity'),
                'decision': item.get('decision')
            }
            if cls == "dent":
                base['depth'] = item.get('depth')
            else:
                base['length'] = item.get('length')

            formatted_results[normalized_cls] = base
        else:
            formatted_results[normalized_cls] = None

    final_output = {
        'results': formatted_results,
        'final_image': result['final_image']
    }

    print(f"Final analysis result: {formatted_results}")

    sample_input = prepare_sample_input(result, filename)
    print(f"Prepared sample input: {sample_input}")

    os.makedirs("sessions", exist_ok=True)
    background_tasks.add_task(background_processing, result, filename, damage_type, session_id, email_name, model)

    return JSONResponse(content={
        "status": True,
        "session_id": session_id,
        "result": final_output,
        "message": "Initial analysis done. Further processing is happening in the background."
    })

   
@app.get("/", tags=["Health Check"])
def healthcheck():
    """
    Simple health check endpoint for the API.
    Returns a JSON response indicating API status.
    """
    return JSONResponse(status_code=200, content={"status": "ok"})


if __name__ == "__main__":
    # Local development server: http://127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)


