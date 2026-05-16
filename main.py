import os
import sys
import cv2
import numpy as np
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
TOLERANCE = 80  # Lower means stricter recognition
MIN_FACE_SIZE = (80, 80)
FONT = cv2.FONT_HERSHEY_SIMPLEX
DATE_COLOR = (0, 255, 0)
DATE_FONT_SCALE = 1.0
DATE_THICKNESS = 2

# Ensure required folders exist
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
recognizer = None
label_ids = {}
id_to_name = {}


def sanitize_label(label: str) -> str:
    return "_".join(label.strip().split())


def detect_faces(gray_image):
    if face_cascade is None or face_cascade.empty():
        return []
    return face_cascade.detectMultiScale(
        gray_image,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=MIN_FACE_SIZE,
    )


def make_face_image(image, rect):
    x, y, w, h = rect
    face = image[y:y+h, x:x+w]
    return cv2.resize(face, (200, 200), interpolation=cv2.INTER_AREA)


def train_recognizer():
    global recognizer, label_ids, id_to_name
    images = []
    labels = []
    label_ids = {}
    id_to_name = {}
    next_id = 0

    for filename in sorted(os.listdir(KNOWN_FACES_DIR)):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        path = os.path.join(KNOWN_FACES_DIR, filename)
        image = cv2.imread(path)
        if image is None:
            continue
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = detect_faces(gray)
        if len(faces) == 0:
            print(f"Skipping {filename}: no face detected.")
            continue

        rect = faces[0]
        face_image = make_face_image(gray, rect)
        label_text = os.path.splitext(filename)[0]
        if "_" in label_text:
            label_text = label_text.rsplit("_", 1)[0]
        label_text = sanitize_label(label_text)

        if label_text not in label_ids:
            label_ids[label_text] = next_id
            id_to_name[next_id] = label_text
            next_id += 1

        images.append(face_image)
        labels.append(label_ids[label_text])

    if len(images) > 0:
        try:
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.train(images, np.array(labels))
            print(f"Trained recognizer on {len(images)} face samples for {len(label_ids)} label(s).")
        except Exception as e:
            recognizer = None
            print(f"Failed to initialize face recognizer: {e}")
    else:
        recognizer = None
        print("No known face training data found. Add images to known_faces/ and restart or use 'a' to capture faces.")


train_recognizer()


def predict_face(face_gray):
    if recognizer is None:
        return "Unknown", None
    try:
        label_id, confidence = recognizer.predict(face_gray)
        name = id_to_name.get(label_id, "Unknown")
        if confidence > TOLERANCE:
            return "Unknown", confidence
        return name, confidence
    except Exception:
        return "Unknown", None


def add_face_from_camera(cam, name, num_photos=3):
    label = sanitize_label(name)
    if not label:
        print("Invalid name.")
        return

    captured = 0
    attempts = 0
    max_attempts = num_photos * 60

    while captured < num_photos and attempts < max_attempts:
        attempts += 1
        ret, frame = cam.read()
        if not ret:
            print("Failed reading from camera.")
            break

        display = frame.copy()
        status_text = f"Capturing {label}: {captured + 1}/{num_photos}"
        cv2.putText(display, status_text, (10, 30), FONT, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.imshow('Face Attendance', display)
        cv2.waitKey(100)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detect_faces(gray)
        if len(faces) == 0:
            if attempts % 10 == 0:
                print("  No face detected, please move into view or improve lighting...")
            continue

        rect = faces[0]
        x, y, w, h = rect
        if w < MIN_FACE_SIZE[0] or h < MIN_FACE_SIZE[1]:
            print("  Face too small, move closer.")
            continue

        filename = os.path.join(KNOWN_FACES_DIR, f"{label}_{captured + 1}.jpg")
        cv2.imwrite(filename, frame)
        print(f"Saved: {filename}")
        captured += 1

    if captured > 0:
        print(f"Captured {captured} photo(s) for '{label}'. Retraining recognizer...")
        train_recognizer()
    else:
        print("No faces captured.")


def import_images(paths, label):
    label = sanitize_label(label)
    if not label:
        print("Invalid label.")
        return

    existing = [f for f in os.listdir(KNOWN_FACES_DIR) if f.lower().startswith(label.lower())]
    start_idx = 1
    if existing:
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
    for path in paths:
        path = path.strip()
        if not path:
            continue
        if not os.path.isabs(path):
            print(f"Path not absolute, skipping: {path}")
            continue
        if not os.path.exists(path):
            print(f"File not found, skipping: {path}")
            continue

        ext = os.path.splitext(path)[1]
        dest_name = f"{label}_{start_idx + added}{ext}"
        dest_path = os.path.join(KNOWN_FACES_DIR, dest_name)
        try:
            shutil.copy2(path, dest_path)
            print(f"Copied {path} -> {dest_path}")
            image = cv2.imread(dest_path)
            if image is None:
                print(f"  Could not read copied image, removing {dest_name}.")
                os.remove(dest_path)
                continue

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = detect_faces(gray)
            if len(faces) == 0:
                print(f"  No face detected in {dest_name}; removing file.")
                os.remove(dest_path)
                continue

            added += 1
        except Exception as e:
            print(f"Failed to import {path}: {e}")

    if added > 0:
        print(f"Imported and saved {added} image(s) for '{label}'. Retraining recognizer...")
        train_recognizer()
    else:
        print("No images imported.")


video = cv2.VideoCapture(0)
if not video.isOpened():
    raise RuntimeError("Could not open webcam. Please make sure your camera is available.")

while True:
    ret, frame = video.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detect_faces(gray)

    now_str = datetime.now().strftime("%A, %d %B %Y %H:%M:%S")
    (text_w, text_h), _ = cv2.getTextSize(now_str, FONT, DATE_FONT_SCALE, DATE_THICKNESS)
    padding = 10
    cv2.rectangle(frame, (5, 5), (10 + text_w + padding, 10 + text_h + padding), (0, 0, 0), cv2.FILLED)
    cv2.putText(frame, now_str, (10, 10 + text_h), FONT, DATE_FONT_SCALE, DATE_COLOR, DATE_THICKNESS, cv2.LINE_AA)

    for (x, y, w, h) in faces:
        face_gray = make_face_image(gray, (x, y, w, h))
        name, confidence = predict_face(face_gray)
        label_text = f"{name}"
        if confidence is not None and name != "Unknown":
            label_text = f"{name} ({confidence:.1f})"

        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        (nw, nh), _ = cv2.getTextSize(label_text, FONT, 0.8, 2)
        cv2.rectangle(frame, (x, y + h + 5), (x + nw + 10, y + h + nh + 10), (0, 0, 0), cv2.FILLED)
        cv2.putText(frame, label_text, (x + 5, y + h + nh + 5), FONT, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.putText(frame, "Press 'a' to add face, 'i' to import, 'q' to quit", (10, frame.shape[0] - 10), FONT, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

    cv2.imshow('Face Attendance', frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('a'):
        print("\n--- Add new face ---")
        name = input("Enter name for new face: ").strip()
        if name:
            add_face_from_camera(video, name, num_photos=3)
        else:
            print("Name empty, cancelled.")
    elif key == ord('i'):
        print("\n--- Import images ---")
        paths_input = input("Enter absolute image paths separated by semicolons: ").strip()
        label = input("Enter label for these images: ").strip()
        if paths_input and label:
            paths = [p.strip() for p in paths_input.split(";")]
            import_images(paths, label)
        else:
            print("Invalid input, cancelled.")
    elif key == ord('q'):
        break

video.release()
cv2.destroyAllWindows()
