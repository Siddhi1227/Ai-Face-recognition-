import os
import sys

# Workaround for pkg_resources issue with face_recognition_models
try:
    import pkg_resources
except ImportError:
    # Mock pkg_resources if it's missing
    import types
    pkg_resources = types.ModuleType('pkg_resources')
    def mock_resource_filename(pkg, resource):
        import face_recognition_models
        base_path = os.path.dirname(face_recognition_models.__file__)
        return os.path.join(base_path, resource)
    pkg_resources.resource_filename = mock_resource_filename
    sys.modules['pkg_resources'] = pkg_resources

import cv2
try:
    import face_recognition
except Exception as _e:
    face_recognition = None
    print("Warning: 'face_recognition' could not be imported. Install with: pip install cmake dlib face_recognition")
import numpy as np
from datetime import datetime
import time
import shutil
import pathlib

FACE_RECO_AVAILABLE = face_recognition is not None

# Configuration
KNOWN_FACES_DIR = os.path.join(os.path.dirname(__file__), "known_faces")
TOLERANCE = 0.6  # Euclidean distance threshold for a match
MODEL = "hog"  # or 'cnn' if you installed GPU-enabled dlib
FONT = cv2.FONT_HERSHEY_SIMPLEX
DATE_COLOR = (0, 255, 0)  # BGR green as requested
DATE_FONT_SCALE = 1.0
DATE_THICKNESS = 2

# Load known faces
known_encodings = []
known_names = []

if not os.path.exists(KNOWN_FACES_DIR):
    os.makedirs(KNOWN_FACES_DIR)

print(f"Loading known faces from: {KNOWN_FACES_DIR}")
if FACE_RECO_AVAILABLE:
    for filename in os.listdir(KNOWN_FACES_DIR):
        if not any(filename.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
            continue
        path = os.path.join(KNOWN_FACES_DIR, filename)
        image = face_recognition.load_image_file(path)
        encs = face_recognition.face_encodings(image)
        if len(encs) == 0:
            print(f"  No faces found in {filename}; skipping.")
            continue
        known_encodings.append(encs[0])
        known_names.append(os.path.splitext(filename)[0])
        print(f"  Loaded {filename} as {known_names[-1]}")
else:
    print("face_recognition unavailable — skipping known faces load. Install required packages to enable recognition.")

if len(known_encodings) == 0:
    print("No known faces loaded. Add images to the 'known_faces' folder and restart.")

# Prepare a fallback OpenCV face detector for when face_recognition isn't available
_face_cascade = None
try:
    _face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
except Exception:
    _face_cascade = None

def sanitize_label(label: str) -> str:
    return "_".join(label.strip().split())

# Function to add a new face from the camera
def add_face_from_camera(cam, name, num_photos=3):
    """Capture num_photos images from the provided camera, save to KNOWN_FACES_DIR as <name>_i.jpg,
    and append their encodings to known_encodings/known_names so recognition updates immediately.
    If face_recognition is not installed, this will still save images using an OpenCV fallback detector.
    """
    print(f"Starting capture for '{name}' — aiming for {num_photos} photos. Look at the camera...")
    captured = 0
    attempts = 0
    max_attempts = num_photos * 60

    while captured < num_photos and attempts < max_attempts:
        attempts += 1
        ret, frame = cam.read()
        if not ret:
            print("Failed reading from camera during capture.")
            break

        display = frame.copy()
        status_text = f"Capturing {name}: {captured + 1}/{num_photos}"
        cv2.putText(display, status_text, (10, 30), FONT, 0.9, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.imshow('Face Attendance', display)
        cv2.waitKey(100)

        # Use a smaller frame for detection
        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        face_detected = False
        enc = None

        if FACE_RECO_AVAILABLE:
            encs = face_recognition.face_encodings(rgb_small)
            if len(encs) > 0:
                face_detected = True
                enc = encs[0]
        else:
            # Fallback: use OpenCV Haar Cascade to check for a face
            if _face_cascade is not None:
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                if len(faces) > 0:
                    face_detected = True

        if face_detected:
            # Save full-size image
            filename = os.path.join(KNOWN_FACES_DIR, f"{name}_{captured + 1}.jpg")
            cv2.imwrite(filename, frame)
            if FACE_RECO_AVAILABLE and enc is not None:
                known_encodings.append(enc)
                known_names.append(name)
                print(f"  Saved and encoded {filename}")
            else:
                # Encoding unavailable now; we'll still save the image for later encoding
                known_names.append(name)
                print(f"  Saved {filename} (encoding skipped; install face_recognition to enable encoding)")
            captured += 1
        else:
            if attempts % 10 == 0:
                print("  No face detected yet, please move into view or improve lighting...")

    if captured == 0:
        print("No faces captured. Try again with better lighting or move closer to camera.")
    else:
        print(f"Captured {captured} photo(s) for '{name}'.")

def import_images(paths, label):
    """Copy images from absolute paths into KNOWN_FACES_DIR as <label>_N.ext,
    extract encodings and add them to known_encodings/known_names.
    If face_recognition isn't available the images are copied and saved but not encoded.
    """
    label = sanitize_label(label)
    # determine starting index by counting existing files with this label
    existing = [f for f in os.listdir(KNOWN_FACES_DIR) if f.lower().startswith(label.lower())]
    start_idx = 1
    if existing:
        # try to find max existing index
        nums = []
        for f in existing:
            name = os.path.splitext(f)[0]
            parts = name.split("_")
            try:
                nums.append(int(parts[-1]))
            except Exception:
                continue
        if nums:
            start_idx = max(nums) + 1

    added = 0
    for p in paths:
        p = p.strip()
        if not p:
            continue
        if not os.path.isabs(p):
            print(f"Path not absolute, skipping: {p}")
            continue
        if not os.path.exists(p):
            print(f"File not found, skipping: {p}")
            continue
        ext = os.path.splitext(p)[1]
        dest_name = f"{label}_{start_idx + added}{ext}"
        dest_path = os.path.join(KNOWN_FACES_DIR, dest_name)
        try:
            shutil.copy2(p, dest_path)
            print(f"Copied {p} -> {dest_path}")
            if FACE_RECO_AVAILABLE:
                image = face_recognition.load_image_file(dest_path)
                encs = face_recognition.face_encodings(image)
                if len(encs) == 0:
                    print(f"  No face found in {dest_name}; removing file.")
                    os.remove(dest_path)
                else:
                    known_encodings.append(encs[0])
                    known_names.append(label)
                    print(f"  Imported and encoded {dest_name} as {label}")
                    added += 1
            else:
                # Keep the copied image; encoding can be done later after installing face_recognition
                known_names.append(label)
                print(f"  Copied {dest_name} (encoding skipped; install face_recognition to enable encoding)")
                added += 1
        except Exception as e:
            print(f"Failed to copy/import {p}: {e}")

    if added == 0:
        print("No new images were imported.")
    else:
        print(f"Imported {added} image(s) for label '{label}'.")

# Start webcam
video = cv2.VideoCapture(0)
if not video.isOpened():
    raise RuntimeError("Could not open webcam")

while True:
    ret, frame = video.read()
    if not ret:
        break

    # Resize frame for faster processing and convert to RGB
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # Detect faces and encodings in the current frame
    if FACE_RECO_AVAILABLE:
        face_locations = face_recognition.face_locations(rgb_small, model=MODEL)
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
    else:
        face_locations = []
        face_encodings = []

    # Draw date (prominent, green) at top-left
    now_str = datetime.now().strftime("%A, %d %B %Y %H:%M:%S")
    (text_w, text_h), _ = cv2.getTextSize(now_str, FONT, DATE_FONT_SCALE, DATE_THICKNESS)
    padding = 10
    cv2.rectangle(frame, (5, 5), (10 + text_w + padding, 10 + text_h + padding), (0, 0, 0), cv2.FILLED)
    cv2.putText(frame, now_str, (10, 10 + text_h), FONT, DATE_FONT_SCALE, DATE_COLOR, DATE_THICKNESS, cv2.LINE_AA)

    # Process each detected face
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        # Restore coordinates because we processed on a scaled frame
        top *= 2
        right *= 2
        bottom *= 2
        left *= 2

        face_width = right - left

        # Proximity sensing: increase font_scale when you lean in
        # If the face_width exceeds 220 pixels (approx), make the name much larger
        if face_width >= 220:
            name_font_scale = 1.6
            name_thickness = 3
        else:
            # Smooth scaling between 0.7 and 1.6
            name_font_scale = 0.7 + (face_width / 220) * (1.6 - 0.7)
            name_font_scale = max(0.6, min(1.6, name_font_scale))
            name_thickness = 2

        name = "Unknown"
        best_distance = None
        if len(known_encodings) > 0:
            # Compute Euclidean distances to all known encodings
            distances = np.linalg.norm(np.array(known_encodings) - face_encoding, axis=1)
            best_idx = np.argmin(distances)
            best_distance = float(distances[best_idx])
            if best_distance <= TOLERANCE:
                name = known_names[best_idx]

        # Draw bounding box
        cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)

        # Draw name background
        name_text = f"{name}"
        (nw, nh), _ = cv2.getTextSize(name_text, FONT, name_font_scale, name_thickness)
        cv2.rectangle(frame, (left, bottom + 5), (left + nw + 10, bottom + 5 + nh + 5), (0, 0, 0), cv2.FILLED)
        cv2.putText(frame, name_text, (left + 5, bottom + 5 + nh), FONT, name_font_scale, (255, 255, 255), name_thickness, cv2.LINE_AA)

        # Optionally show the Euclidean distance for debugging
        # if best_distance is not None:
        #     dist_text = f"{best_distance:.2f}"
        #     cv2.putText(frame, dist_text, (left, top - 10), FONT, 0.6, (0, 255, 255), 1)

    # Draw simple on-screen menu prompt
    menu_text = "Press 'a' to add face, 'q' to quit"
    cv2.putText(frame, menu_text, (10, frame.shape[0] - 10), FONT, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

    cv2.imshow('Face Attendance', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('a'):
        # Pause live loop and request name in terminal
        print("\n--- Add new face ---")
        name = input("Enter name for new face (no spaces recommended): ").strip()
        if name:
            add_face_from_camera(video, name, num_photos=3)
        else:
            print("Name empty, cancelled.")
    if key == ord('q'):
        break
    if key == ord('i'):
        # Import images from paths
        print("\n--- Import images ---")
        paths_input = input("Enter absolute paths of images, separated by semicolons: ").strip()
        label = input("Enter label for these images: ").strip()
        if paths_input and label:
            paths = [p.strip() for p in paths_input.split(";")]
            import_images(paths, label)
        else:
            print("Invalid input, cancelled.")

video.release()
cv2.destroyAllWindows()
