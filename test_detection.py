import os
import cv2

BASE_DIR = os.path.dirname(__file__)
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")

# Load multiple cascade classifiers
cascades = {
    'alt2': cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'),
    'alt': cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml'),
    'default': cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'),
}

print("Testing face detection on known_faces images...\n")

for filename in sorted(os.listdir(KNOWN_FACES_DIR)):
    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        continue
    
    filepath = os.path.join(KNOWN_FACES_DIR, filename)
    image = cv2.imread(filepath)
    
    if image is None:
        print(f"[FAIL] {filename}: Could not read image")
        continue
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    print(f"[INFO] {filename}: size={w}x{h}")
    
    found_any = False
    for cascade_name, cascade in cascades.items():
        if cascade is None or cascade.empty():
            print(f"  {cascade_name}: NOT LOADED")
            continue
        
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=4,
            minSize=(40, 40),
        )
        
        if len(faces) > 0:
            print(f"  {cascade_name}: FOUND {len(faces)} face(s) {faces}")
            found_any = True
        else:
            print(f"  {cascade_name}: no faces found")
    
    if not found_any:
        print(f"  [WARNING] No cascades detected a face in this image!")
    print()
