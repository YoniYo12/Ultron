import cv2
import numpy as np


class ValueMapper:
    """Map hand gestures to control values with smoothing and gating."""
    
    def __init__(self, smoothing_factor=0.5, position_smoothing_factor=0.85, catch_up_factor=0.7):
        """
        Initialize value mapper.
        
        Args:
            smoothing_factor: Smoothing for pinch strength (0-1)
                             Lower = smoother (0.3-0.5)
            position_smoothing_factor: Smoothing for hand position (0-1)
                                      Much higher for direct control (0.85-0.95)
            catch_up_factor: Fast catch-up on pinch start (0-1)
        """
        self.smoothing_factor = smoothing_factor
        self.position_smoothing_factor = position_smoothing_factor
        self.catch_up_factor = catch_up_factor
        
        # Smoothed values
        self.smoothed_pinch_strength = 0.0
        self.smoothed_hand_position = [0.5, 0.5, 0.0]
        
        # Last valid values (held when not pinching)
        self.held_pinch_strength = 0.0
        self.held_hand_position = [0.5, 0.5, 0.0]
        
        # State tracking
        self.is_active = False
        self.was_active_last_frame = False
        self.was_grab_last_frame = False

        # Grab (rotate) pipeline — smoothed confidence + position for delta-based rotation
        self.grab_confidence = 0.0
        self.grab_smoothed_position = [0.5, 0.5, 0.0]
        self._grab_prev_smoothed = [0.5, 0.5, 0.0]
        self.grab_delta_xy = [0.0, 0.0]
        
    def smooth_value(self, current_value, smoothed_value):
        """
        Apply exponential moving average smoothing.
        
        Args:
            current_value: New value to smooth
            smoothed_value: Previous smoothed value
            
        Returns:
            float: Smoothed value
        """
        return self.smoothing_factor * current_value + (1 - self.smoothing_factor) * smoothed_value
    
    def smooth_position(self, current_pos, smoothed_pos):
        """
        Smooth 3D position vector with light smoothing for direct control.
        
        Args:
            current_pos: [x, y, z] current position
            smoothed_pos: [x, y, z] previous smoothed position
            
        Returns:
            list: Lightly smoothed [x, y, z] position
        """
        return [
            self.position_smoothing_factor * current_pos[0] + (1 - self.position_smoothing_factor) * smoothed_pos[0],
            self.position_smoothing_factor * current_pos[1] + (1 - self.position_smoothing_factor) * smoothed_pos[1],
            self.position_smoothing_factor * current_pos[2] + (1 - self.position_smoothing_factor) * smoothed_pos[2]
        ]
    
    def update(self, is_pinching, pinch_strength, hand_center, is_grab=False):
        """
        Pinch has priority over grab. Grab uses the same light position smoothing
        while active, plus confidence EMA so the pipeline isn't "bolted on" raw.

        Returns position deltas for rotation (movement-based, not screen-center angle).
        """
        grab_rate = 0.32
        self.grab_delta_xy = [0.0, 0.0]

        if is_pinching:
            pinch_just_started = is_pinching and not self.was_active_last_frame
            if pinch_just_started:
                self.smoothed_pinch_strength = self.catch_up_factor * pinch_strength + (1 - self.catch_up_factor) * self.smoothed_pinch_strength
                self.smoothed_hand_position = [
                    0.9 * hand_center[0] + 0.1 * self.smoothed_hand_position[0],
                    0.9 * hand_center[1] + 0.1 * self.smoothed_hand_position[1],
                    0.9 * hand_center[2] + 0.1 * self.smoothed_hand_position[2],
                ]
            else:
                self.smoothed_pinch_strength = self.smooth_value(pinch_strength, self.smoothed_pinch_strength)
                self.smoothed_hand_position = self.smooth_position(hand_center, self.smoothed_hand_position)
            self.held_pinch_strength = self.smoothed_pinch_strength
            self.held_hand_position = self.smoothed_hand_position.copy()
            self.is_active = True
            self.grab_confidence *= 0.85
        else:
            self.is_active = False
            if is_grab:
                self.grab_confidence = min(1.0, self.grab_confidence + grab_rate)
                grab_just_started = is_grab and not self.was_grab_last_frame
                if grab_just_started:
                    self.grab_smoothed_position = [
                        0.92 * hand_center[0] + 0.08 * self.grab_smoothed_position[0],
                        0.92 * hand_center[1] + 0.08 * self.grab_smoothed_position[1],
                        0.92 * hand_center[2] + 0.08 * self.grab_smoothed_position[2],
                    ]
                    self._grab_prev_smoothed = self.grab_smoothed_position.copy()
                else:
                    self.grab_smoothed_position = self.smooth_position(hand_center, self.grab_smoothed_position)
                self.grab_delta_xy = [
                    self.grab_smoothed_position[0] - self._grab_prev_smoothed[0],
                    self.grab_smoothed_position[1] - self._grab_prev_smoothed[1],
                ]
                self._grab_prev_smoothed = self.grab_smoothed_position.copy()
            else:
                self.grab_confidence = max(0.0, self.grab_confidence - grab_rate * 1.2)

        self.was_active_last_frame = is_pinching
        self.was_grab_last_frame = is_grab

        is_rotating = (not is_pinching) and (self.grab_confidence > 0.68)

        return {
            'pinch_strength': self.held_pinch_strength,
            'position': self.held_hand_position,
            'is_active': is_pinching,
            'is_rotating': is_rotating,
            'grab_position': self.grab_smoothed_position.copy(),
            'grab_delta_xy': list(self.grab_delta_xy),
            'grab_confidence': self.grab_confidence,
        }
    
    def map_to_radius(self, pinch_strength, min_radius=20, max_radius=200):
        """
        Map pinch strength to circle radius.
        
        Args:
            pinch_strength: Smoothed pinch strength (0-1)
            min_radius: Minimum circle size
            max_radius: Maximum circle size
            
        Returns:
            int: Circle radius in pixels
        """
        radius = int(min_radius + pinch_strength * (max_radius - min_radius))
        return radius
    
    def map_to_scale(self, pinch_strength, min_scale=0.2, max_scale=2.0):
        """
        Map pinch strength to scale factor.
        
        Args:
            pinch_strength: Smoothed pinch strength (0-1)
            min_scale: Minimum scale
            max_scale: Maximum scale
            
        Returns:
            float: Scale factor
        """
        return min_scale + pinch_strength * (max_scale - min_scale)
    
    def map_to_screen_position(self, hand_position, screen_width, screen_height):
        """
        Map normalized hand position (0-1) to screen coordinates.
        
        Args:
            hand_position: [x, y, z] normalized (0-1)
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            
        Returns:
            tuple: (x, y) screen coordinates
        """
        x = int(hand_position[0] * screen_width)
        y = int(hand_position[1] * screen_height)
        return (x, y)
    
    def reset(self):
        """Reset all smoothed values."""
        self.smoothed_pinch_strength = 0.0
        self.smoothed_hand_position = [0.5, 0.5, 0.0]
        self.held_pinch_strength = 0.0
        self.held_hand_position = [0.5, 0.5, 0.0]
        self.is_active = False
        self.was_grab_last_frame = False
        self.grab_confidence = 0.0
        self.grab_smoothed_position = [0.5, 0.5, 0.0]
        self._grab_prev_smoothed = [0.5, 0.5, 0.0]
        self.grab_delta_xy = [0.0, 0.0]


class VisualFeedback:
    """Render visual feedback for gesture control in 2D."""
    
    @staticmethod
    def draw_control_circle(frame, position, radius, is_active):
        """
        Draw a circle that responds to pinch control.
        
        Args:
            frame: OpenCV frame
            position: (x, y) center position
            radius: Circle radius
            is_active: True if pinching (changes color)
        """
        # Color: Green when active, Blue when inactive
        color = (0, 255, 0) if is_active else (255, 100, 100)
        
        # Draw filled circle
        cv2.circle(frame, position, radius, color, -1)
        
        # Draw outline
        cv2.circle(frame, position, radius, (255, 255, 255), 2)
        
        return frame
    
    @staticmethod
    def draw_control_rectangle(frame, center, size, is_active):
        """
        Draw a rectangle that responds to pinch control.
        
        Args:
            frame: OpenCV frame
            center: (x, y) center position
            size: Rectangle size (will be size x size)
            is_active: True if pinching (changes color)
        """
        x, y = center
        half_size = size // 2
        
        top_left = (x - half_size, y - half_size)
        bottom_right = (x + half_size, y + half_size)
        
        # Color: Green when active, Blue when inactive
        color = (0, 255, 0) if is_active else (255, 100, 100)
        
        # Draw filled rectangle
        cv2.rectangle(frame, top_left, bottom_right, color, -1)
        
        # Draw outline
        cv2.rectangle(frame, top_left, bottom_right, (255, 255, 255), 2)
        
        return frame
    
    @staticmethod
    def draw_status_panel(frame, pinch_strength, is_active, raw_strength=None):
        """
        Draw status information panel.
        
        Args:
            frame: OpenCV frame
            pinch_strength: Smoothed pinch strength value
            is_active: True if pinching
            raw_strength: Optional raw (unsmoothed) strength for comparison
        """
        h, w = frame.shape[:2]
        
        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, h - 150), (350, h - 10), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Status text
        y_offset = h - 120
        cv2.putText(frame, "PINCH CONTROL", (20, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        y_offset += 30
        status = "ACTIVE" if is_active else "INACTIVE"
        status_color = (0, 255, 0) if is_active else (100, 100, 255)
        cv2.putText(frame, f"State: {status}", (20, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2)
        
        y_offset += 25
        cv2.putText(frame, f"Smoothed: {pinch_strength:.3f}", (20, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        if raw_strength is not None:
            y_offset += 25
            cv2.putText(frame, f"Raw: {raw_strength:.3f}", (20, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # Progress bar for pinch strength
        bar_x = 20
        bar_y = h - 30
        bar_width = 310
        bar_height = 15
        
        # Background bar
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     (50, 50, 50), -1)
        
        # Filled bar
        filled_width = int(pinch_strength * bar_width)
        if filled_width > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled_width, bar_y + bar_height), 
                         (0, 255, 0), -1)
        
        return frame


if __name__ == "__main__":
    from hand_tracking import HandTracker
    from gestures import GestureRecognizer
    
    # Initialize
    cap = cv2.VideoCapture(0)
    tracker = HandTracker()
    gesture = GestureRecognizer(pinch_threshold=0.05)
    mapper = ValueMapper(
        smoothing_factor=0.5,           # Strength: smooth
        position_smoothing_factor=0.85, # Position: direct & fast
        catch_up_factor=0.7
    )
    visual = VisualFeedback()
    
    print("=== PINCH CONTROL DEMO ===")
    print("Instructions:")
    print("  - Pinch your fingers together to activate")
    print("  - While pinching, adjust pinch strength to scale circle")
    print("  - Move your hand to move the circle")
    print("  - Release to hold position and size")
    print("  - Press 'q' to quit")
    print()
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        # Get frame dimensions
        h, w = frame.shape[:2]
        
        # Flip for mirror effect
        frame = cv2.flip(frame, 1)
        
        # Process hand tracking
        tracker.process_frame(frame)
        
        # Draw hand skeleton (optional, comment out for cleaner view)
        # frame = tracker.draw_landmarks(frame)
        
        hands_info = tracker.get_hand_info()
        
        if hands_info:
            # Use first detected hand
            hand = hands_info[0]
            landmarks = hand['landmarks']
            
            # Get gesture data
            is_pinching = gesture.is_pinching(landmarks)
            raw_strength = gesture.get_pinch_strength(landmarks)
            hand_center = gesture.get_hand_center(landmarks)
            
            # Update mapper with gating
            control_data = mapper.update(is_pinching, raw_strength, hand_center, False)
            
            # Get smoothed & gated values
            smoothed_strength = control_data['pinch_strength']
            smoothed_position = control_data['position']
            is_active = control_data['is_active']
            
            # Map to visual properties
            radius = mapper.map_to_radius(smoothed_strength, min_radius=30, max_radius=150)
            screen_pos = mapper.map_to_screen_position(smoothed_position, w, h)
            
            # Draw control circle
            visual.draw_control_circle(frame, screen_pos, radius, is_active)
            
            # Draw status panel
            visual.draw_status_panel(frame, smoothed_strength, is_active, raw_strength)
            
            # Draw hand label
            cv2.putText(frame, f"{hand['handedness']} Hand", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        else:
            # No hand detected
            cv2.putText(frame, "No hand detected", (w//2 - 100, h//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Display
        cv2.imshow('Pinch Control Demo - 2D', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    tracker.close()
