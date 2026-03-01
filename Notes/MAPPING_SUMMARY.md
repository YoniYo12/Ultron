# Mapping Module Summary

## Purpose
Convert jittery hand tracking into smooth, intentional control signals.

## Two Core Techniques

### 1. Smoothing (Exponential Moving Average)
Blends new values with old values to reduce jitter:
```python
smooth_value = 0.5 * new_value + 0.5 * old_value
```
- Lower smoothing_factor (0.1-0.3) = smoother but slower
- Higher smoothing_factor (0.5-0.7) = faster and responsive (recommended)

### 2. Gating (State-Based Updates)
**Rule:** Only update when pinching, hold when released
```python
if is_pinching:
    smooth_and_update()  # Active control
else:
    hold_last_value()    # Freeze in place
```
Makes control feel intentional, like "grabbing" the object.

### 3. Fast Catch-Up (Removes Initial Lag)
On the first frame of pinching, snap closer to target:
```python
if pinch_just_started:
    smooth_value = 0.7 * new_value + 0.3 * old_value  # Fast catch-up
else:
    smooth_value = 0.5 * new_value + 0.5 * old_value  # Normal smoothing
```
Eliminates the "slow start" feeling when you begin pinching.

## Key Class: ValueMapper

### Initialize
```python
mapper = ValueMapper(
    smoothing_factor=0.5,    # 0.5-0.6 for fast response
    catch_up_factor=0.7      # 0.7 for quick initial snap
)
```

### Update (every frame)
```python
control_data = mapper.update(
    is_pinching=True/False,
    pinch_strength=0.0-1.0,
    hand_center=[x, y, z]
)
```

### Get Results
```python
control_data['pinch_strength']  # Smoothed strength (only updates when pinching)
control_data['position']        # Smoothed position [x, y, z]
control_data['is_active']       # True if pinching
```

## Mapping Functions

```python
# Pinch strength → circle radius
radius = mapper.map_to_radius(pinch_strength, min_radius=20, max_radius=200)

# Pinch strength → scale factor
scale = mapper.map_to_scale(pinch_strength, min_scale=0.2, max_scale=2.0)

# Hand position → screen coordinates
x, y = mapper.map_to_screen_position(hand_position, screen_width, screen_height)
```

## Complete Usage Example

```python
from hand_tracking import HandTracker
from gestures import GestureRecognizer
from mapping import ValueMapper

tracker = HandTracker()
gesture = GestureRecognizer()
mapper = ValueMapper(smoothing_factor=0.5, catch_up_factor=0.7)

while True:
    frame = capture_frame()
    tracker.process_frame(frame)
    hands_info = tracker.get_hand_info()
    
    for hand in hands_info:
        landmarks = hand['landmarks']
        
        # Raw data
        is_pinching = gesture.is_pinching(landmarks)
        raw_strength = gesture.get_pinch_strength(landmarks)
        hand_center = gesture.get_hand_center(landmarks)
        
        # Apply smoothing + gating
        control = mapper.update(is_pinching, raw_strength, hand_center)
        
        # Use smooth values for control
        radius = mapper.map_to_radius(control['pinch_strength'])
        position = mapper.map_to_screen_position(control['position'], w, h)
        
        draw_circle(position, radius, control['is_active'])
```

## Test It

```bash
cd src
python mapping.py
```

**Demo shows:**
- Circle follows hand (smoothly)
- Pinch to activate (green = active, blue = held)
- Adjust pinch strength to scale circle
- Release → circle freezes in place
- Status panel with raw vs smoothed values

## The Flow

```
Raw Tracking → Gesture Detection → Mapping → Control
  (jittery)       (pinch detect)    (smooth)   (3D object)
```

## Why This Matters

**Without mapping:**
- Object shakes constantly
- Can't hold position steady
- Feels uncontrollable

**With mapping:**
- Smooth movements
- Hold position when released
- Feels natural and precise
