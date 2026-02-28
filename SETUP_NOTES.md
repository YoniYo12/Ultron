# Hand Tracking Setup - Step by Step Explanation

## Problem You Had

You were getting this error:
```
AttributeError: module 'mediapipe' has no attribute 'solutions'
```

## Root Cause

**Python 3.13 Compatibility Issue**
- You're using Python 3.13
- MediaPipe version 0.10.32 doesn't include the old `solutions` API on Python 3.13
- Only the newer `tasks` API is available

## What I Fixed

### Step 1: Changed the MediaPipe API
**Before (old code - doesn't work on Python 3.13):**
```python
mp.solutions.hands  # This doesn't exist in your version
mp.solutions.drawing_utils
```

**After (new code - works with Python 3.13):**
```python
mp.tasks.vision.HandLandmarker  # New tasks API
mp.tasks.vision.HandLandmarkerOptions
mp.tasks.vision.RunningMode.VIDEO
```

### Step 2: Model Download
The tasks API requires a model file. I added code to auto-download it:
```python
if not os.path.exists('hand_landmarker.task'):
    url = 'https://storage.googleapis.com/mediapipe-models/...'
    urllib.request.urlretrieve(url, model_path)
```

### Step 3: Changed Detection Mode
**Before:**
```python
hands = mp.solutions.hands.Hands(static_image_mode=False, ...)
results = hands.process(frame)
```

**After:**
```python
landmarker = HandLandmarker.create_from_options(options)
results = landmarker.detect_for_video(mp_image, timestamp_ms)
```

### Step 4: Drawing Landmarks
Since `mp_drawing` utilities don't exist, I manually drew:
- Hand skeleton connections (lines between landmarks)
- Joint positions (circles at each landmark)

## What the HandTracker Class Does

### Initialization (`__init__`)
1. Downloads the hand landmarker model if needed
2. Creates a HandLandmarker with VIDEO mode
3. Sets confidence thresholds for detection

### Processing (`process_frame`)
1. Converts frame from BGR to RGB
2. Creates MediaPipe Image object
3. Runs hand detection
4. Returns processed frame

### Getting Data
- `get_hand_landmarks()` - Raw landmark data
- `get_hand_info()` - Landmarks + left/right hand labels
- `get_landmark_positions()` - Pixel coordinates (x, y, z)

### Visualization (`draw_landmarks`)
1. Draws green lines connecting the 21 hand landmarks
2. Draws pink circles at each joint position
3. Shows the hand skeleton overlay

## How to Use It

### Basic Usage
```python
from hand_tracking import HandTracker

cap = cv2.VideoCapture(0)
tracker = HandTracker()

while cap.isOpened():
    success, frame = cap.read()
    frame = cv2.flip(frame, 1)  # Mirror effect
    
    tracker.process_frame(frame)
    frame = tracker.draw_landmarks(frame)
    
    cv2.imshow('Hand Tracking', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
```

### Getting Hand Data for 3D Control
```python
# Get detailed info
hands_info = tracker.get_hand_info()
for hand in hands_info:
    print(f"Hand: {hand['handedness']}")  # "Left" or "Right"
    landmarks = hand['landmarks']  # 21 landmarks
    
# Get pixel positions
positions = tracker.get_landmark_positions(frame_width, frame_height)
for hand_positions in positions:
    # hand_positions is a list of 21 (x, y, z) tuples
    thumb_tip = hand_positions[4]  # Landmark 4 is thumb tip
    index_tip = hand_positions[8]  # Landmark 8 is index finger tip
```

## MediaPipe Hand Landmarks (21 points)

Each hand has 21 landmarks:
```
0  - WRIST
1  - THUMB_CMC
2  - THUMB_MCP
3  - THUMB_IP
4  - THUMB_TIP
5  - INDEX_FINGER_MCP
6  - INDEX_FINGER_PIP
7  - INDEX_FINGER_DIP
8  - INDEX_FINGER_TIP
9  - MIDDLE_FINGER_MCP
10 - MIDDLE_FINGER_PIP
11 - MIDDLE_FINGER_DIP
12 - MIDDLE_FINGER_TIP
13 - RING_FINGER_MCP
14 - RING_FINGER_PIP
15 - RING_FINGER_DIP
16 - RING_FINGER_TIP
17 - PINKY_MCP
18 - PINKY_PIP
19 - PINKY_DIP
20 - PINKY_TIP
```

## Next Steps for 3D Object Control

Once hand tracking is working:
1. Add gesture detection (pinch = thumb + index finger close together)
2. Map hand position to 3D space
3. Create 3D rendering with Pygame + PyOpenGL
4. Link gestures to object manipulation (grab, move, rotate)

## Testing

Run:
```bash
cd src
python hand_tracking.py
```

Expected output:
- Webcam opens
- Green skeleton lines on your hands
- Pink dots at joints
- "Left Hand" / "Right Hand" labels
- Press 'q' to quit
