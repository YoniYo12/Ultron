# Gesture Detection - Step by Step Explanation

## Goal
Implement pinch distance detection to measure the distance between thumb tip and index finger tip.

## Step-by-Step Breakdown

### Step 1: Understanding Hand Landmarks

MediaPipe provides 21 landmarks per hand:
```
Landmark 0  = WRIST
Landmark 4  = THUMB_TIP
Landmark 8  = INDEX_TIP
Landmark 12 = MIDDLE_TIP
Landmark 16 = RING_TIP
Landmark 20 = PINKY_TIP
```

Each landmark has:
- `x` - Horizontal position (0-1, normalized)
- `y` - Vertical position (0-1, normalized)
- `z` - Depth relative to wrist (negative = toward camera)

### Step 2: Calculate Distance Between Two Points

To find distance between thumb and index finger, we use **3D Euclidean distance**:

```python
def calculate_distance(self, landmark1, landmark2):
    dx = landmark1.x - landmark2.x  # Horizontal difference
    dy = landmark1.y - landmark2.y  # Vertical difference
    dz = landmark1.z - landmark2.z  # Depth difference
    
    # Pythagorean theorem in 3D
    return math.sqrt(dx*dx + dy*dy + dz*dz)
```

**Why 3D?**
- Hand can move forward/backward (z-axis matters)
- Using only x,y would miss depth changes
- More accurate for gesture detection

### Step 3: Get Pinch Distance

Extract thumb tip and index tip, then calculate distance:

```python
def get_pinch_distance(self, hand_landmarks):
    thumb_tip = hand_landmarks[4]   # Landmark 4
    index_tip = hand_landmarks[8]   # Landmark 8
    
    return self.calculate_distance(thumb_tip, index_tip)
```

**Returns:** Normalized distance (usually 0.01 to 0.3)
- 0.01-0.05 = Very close (pinching)
- 0.05-0.15 = Moderate distance
- 0.15+ = Fingers far apart

### Step 4: Detect If Pinching

Compare distance to a threshold:

```python
def is_pinching(self, hand_landmarks):
    distance = self.get_pinch_distance(hand_landmarks)
    return distance < self.pinch_threshold  # Default: 0.05
```

**Logic:**
- If distance < threshold → Pinching = True
- If distance ≥ threshold → Pinching = False

**Threshold of 0.05 means:**
- Thumb and index must be within ~5% of screen size
- Adjust in `__init__` if too sensitive/insensitive

### Step 5: Calculate Pinch Strength

Convert distance to a 0-1 scale (inverse relationship):

```python
def get_pinch_strength(self, hand_landmarks):
    distance = self.get_pinch_distance(hand_landmarks)
    max_distance = 0.15  # Maximum expected distance
    
    # Invert: small distance = high strength
    strength = 1.0 - min(distance / max_distance, 1.0)
    
    # Clamp to 0-1 range
    return max(0.0, strength)
```

**How it works:**
```
distance = 0.00 → strength = 1.0 (100% pinched)
distance = 0.05 → strength = 0.67 (67% pinched)
distance = 0.10 → strength = 0.33 (33% pinched)
distance = 0.15+ → strength = 0.0 (0% pinched)
```

**Use case:** Gradual control (e.g., object size scales with pinch strength)

## Additional Gestures Implemented

### Grab Detection (Fist)
Check if all fingertips are close to wrist:

```python
def is_grabbing(self, hand_landmarks):
    wrist = hand_landmarks[0]
    
    # Measure distance from wrist to each fingertip
    distances = [
        self.calculate_distance(wrist, hand_landmarks[8]),   # Index
        self.calculate_distance(wrist, hand_landmarks[12]),  # Middle
        self.calculate_distance(wrist, hand_landmarks[16]),  # Ring
        self.calculate_distance(wrist, hand_landmarks[20])   # Pinky
    ]
    
    avg_distance = sum(distances) / len(distances)
    return avg_distance < 0.15  # Threshold for closed fist
```

### Open Palm Detection
Check if all fingertips are far from wrist:

```python
def is_open_palm(self, hand_landmarks):
    wrist = hand_landmarks[0]
    
    distances = [...]  # Same as grab
    avg_distance = sum(distances) / len(distances)
    return avg_distance > 0.25  # Threshold for open hand
```

### Pointing Detection
Index extended, others closed:

```python
def is_pointing(self, hand_landmarks):
    wrist = hand_landmarks[0]
    
    index_extended = self.calculate_distance(wrist, hand_landmarks[8]) > 0.20
    middle_closed = self.calculate_distance(wrist, hand_landmarks[12]) < 0.15
    ring_closed = self.calculate_distance(wrist, hand_landmarks[16]) < 0.15
    
    return index_extended and middle_closed and ring_closed
```

## Utility Functions

### Get Hand Center
Average position of all 21 landmarks:

```python
def get_hand_center(self, hand_landmarks):
    x = sum(lm.x for lm in hand_landmarks) / 21
    y = sum(lm.y for lm in hand_landmarks) / 21
    z = sum(lm.z for lm in hand_landmarks) / 21
    return (x, y, z)
```

**Use case:** Track hand position for moving 3D objects

### Get Hand Rotation
Calculate angle from wrist to middle finger base:

```python
def get_hand_rotation(self, hand_landmarks):
    wrist = hand_landmarks[0]
    middle_mcp = hand_landmarks[9]  # Middle finger base
    
    dx = middle_mcp.x - wrist.x
    dy = middle_mcp.y - wrist.y
    
    angle = math.degrees(math.atan2(dy, dx))
    return angle
```

**Use case:** Rotate objects based on hand orientation

### Two Hand Distance
Distance between centers of two hands:

```python
def get_two_hand_distance(self, hand1_landmarks, hand2_landmarks):
    center1 = self.get_hand_center(hand1_landmarks)
    center2 = self.get_hand_center(hand2_landmarks)
    
    dx = center1[0] - center2[0]
    dy = center1[1] - center2[1]
    dz = center1[2] - center2[2]
    
    return math.sqrt(dx*dx + dy*dy + dz*dz)
```

**Use case:** Pinch-to-zoom with two hands, scaling objects

## How to Use the GestureRecognizer

### Basic Setup

```python
from hand_tracking import HandTracker
from gestures import GestureRecognizer

tracker = HandTracker()
gesture = GestureRecognizer(pinch_threshold=0.05)

cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    frame = cv2.flip(frame, 1)
    
    # Process frame
    tracker.process_frame(frame)
    hands_info = tracker.get_hand_info()
    
    for hand in hands_info:
        landmarks = hand['landmarks']
        
        # Get pinch info
        distance = gesture.get_pinch_distance(landmarks)
        is_pinching = gesture.is_pinching(landmarks)
        strength = gesture.get_pinch_strength(landmarks)
        
        print(f"Distance: {distance:.3f}, Pinching: {is_pinching}, Strength: {strength:.2f}")
```

### Real-World Example: Grab and Move Object

```python
# State tracking
object_grabbed = False
object_position = [0.5, 0.5]  # Center of screen

for hand in hands_info:
    landmarks = hand['landmarks']
    
    # Detect pinch to grab
    if gesture.is_pinching(landmarks) and not object_grabbed:
        object_grabbed = True
        print("Object grabbed!")
    
    # Move object while grabbing
    if object_grabbed:
        center = gesture.get_hand_center(landmarks)
        object_position = [center[0], center[1]]
    
    # Release on open palm
    if gesture.is_open_palm(landmarks):
        object_grabbed = False
        print("Object released!")
```

### Adjust Sensitivity

Change thresholds based on your needs:

```python
# More sensitive (easier to trigger pinch)
gesture = GestureRecognizer(pinch_threshold=0.08)

# Less sensitive (requires closer pinch)
gesture = GestureRecognizer(pinch_threshold=0.03)
```

## Testing the Implementation

Run the demo:
```bash
cd src
python gestures.py
```

**What you'll see:**
- Live hand tracking with skeleton overlay
- Real-time pinch distance (e.g., 0.052)
- Pinching status (True/False)
- Pinch strength (0.00 to 1.00)
- "GRABBING" label when making a fist
- "OPEN PALM" label when hand is open

## Common Distance Values

Based on testing:
```
Pinching (touching):     0.01 - 0.03
Almost pinching:         0.03 - 0.05
Fingers separated:       0.05 - 0.10
Fingers wide apart:      0.10 - 0.20
Maximum separation:      0.20+
```

## Next Steps for 3D Control

Now that you have gesture detection:

1. **Map hand position to 3D space**
   ```python
   hand_center = gesture.get_hand_center(landmarks)
   object_3d_pos = [hand_center[0] * 2 - 1,  # Convert 0-1 to -1 to 1
                    1 - hand_center[1] * 2,   # Flip Y axis
                    hand_center[2] * 5]       # Scale Z depth
   ```

2. **Control object with pinch**
   - Pinch + move = translate object
   - Two hands pinch = rotate/scale object
   - Open palm = release object

3. **Add smoothing** (reduce jitter)
   ```python
   # Simple moving average
   smooth_pos = 0.7 * current_pos + 0.3 * previous_pos
   ```

4. **Create 3D rendering** with Pygame + PyOpenGL
   - Render a 3D cube
   - Update cube position from hand center
   - Update cube size from pinch strength
