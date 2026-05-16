# AI Face Recognition Attendance System

A lightweight real-time face attendance app built using Python and OpenCV. This version runs without `dlib` or `face_recognition`, so it is much easier to install on Windows.

## Setup

1. Open PowerShell in the project folder:
```powershell
cd c:\Users\dell\Pictures\Documents\GitHub\Ai-Face-recognition-
```

2. Activate the virtual environment:
```powershell
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:
```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

## Run the app

```powershell
python main.py
```

## What the app does

- Opens your webcam
- Detects faces using OpenCV Haar Cascades
- Recognizes known faces using OpenCV LBPH face recognition
- Shows the current date/time in green at top-left
- Saves known face images to `known_faces/`
- Supports adding new faces from camera and importing image files

## Folders

- `known_faces/` — store labeled face images here
- `assets/` — available for future assets or UI files
- `.venv/` — Python virtual environment

## Controls

- Press `a` to add a new face from the camera
- Press `i` to import face images from disk
- Press `q` to quit

## Adding faces

- Press `a` while the camera view is open
- Type a name and press Enter
- The app captures 3 images and saves them to `known_faces/`

## Importing face images

- Press `i`
- Enter absolute paths separated by semicolons
- Enter a label/name for those images
- The app copies valid face images into `known_faces/`

## Notes

- `opencv-contrib-python` is required for the LBPH recognizer
- If face recognition is not confident, the app will show `Unknown`
- For best results, use clear frontal face photos and good lighting
