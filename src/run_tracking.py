import cv2
import threading
from hand_tracking import HandTracker
from gestures import GestureRecognizer
from mapping import ValueMapper


class TrackingThread:
    """Runs hand tracking in a separate thread."""
    
    def __init__(self, control_data_ref):
        """
        Initialize tracking thread.
        
        Args:
            control_data_ref: Shared dict to store latest control data
        """
        self.control_data = control_data_ref
        self.running = False
        self.thread = None
        
        # Initialize tracking components
        self.tracker = HandTracker()
        self.gesture = GestureRecognizer(pinch_threshold=0.05)
        self.mapper = ValueMapper(
            smoothing_factor=0.5,
            position_smoothing_factor=0.85,
            catch_up_factor=0.7
        )
        
        # Optional: Show camera feed
        self.show_camera = True
    
    def start(self):
        """Start the tracking thread."""
        self.running = True
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        print("Tracking thread started!")
    
    def stop(self):
        """Stop the tracking thread."""
        self.running = False
        if self.thread:
            self.thread.join()
        print("Tracking thread stopped!")
    
    def _tracking_loop(self):
        """Main tracking loop (runs in separate thread)."""
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("ERROR: Could not open camera!")
            return
        
        print("Camera opened. Tracking hands...")
        
        while self.running and cap.isOpened():
            success, frame = cap.read()
            if not success:
                continue
            
            # Flip for mirror effect
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            
            # Process hand tracking
            self.tracker.process_frame(frame)
            hands_info = self.tracker.get_hand_info()
            
            if hands_info:
                try:
                    # Use first detected hand for control
                    hand = hands_info[0]
                    landmarks = hand['landmarks']
                    
                    # Compute gesture data
                    is_pinching = self.gesture.is_pinching(landmarks)
                    is_grabbing = self.gesture.is_grabbing(landmarks)
                    raw_strength = self.gesture.get_pinch_strength(landmarks)
                    hand_center = self.gesture.get_hand_center(landmarks)
                    hand_3d_orientation = self.gesture.get_hand_3d_orientation(landmarks)
                    
                    # Prioritize gestures: grabbing (fist) takes priority over pinching
                    # This prevents conflicts
                    if is_grabbing:
                        # Rotation mode - disable pinching
                        is_pinching = False
                        raw_strength = 0.0
                    
                    # Update mapper (smoothing + gating)
                    control = self.mapper.update(is_pinching, raw_strength, hand_center)
                    
                    # Add rotation data (claw/grab gesture triggers rotation)
                    control['is_rotating'] = is_grabbing
                    control['orientation'] = hand_3d_orientation
                    
                    # Store in shared dict for 3D app
                    self.control_data['latest'] = control
                
                except Exception as e:
                    print(f"Error processing hand data: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                # Optional: Draw on camera feed
                if self.show_camera:
                    frame = self.tracker.draw_landmarks(frame)
                    
                    # Calculate average finger distance for debugging
                    wrist = landmarks[0]
                    distances = [
                        self.gesture.calculate_distance(wrist, landmarks[8]),
                        self.gesture.calculate_distance(wrist, landmarks[12]),
                        self.gesture.calculate_distance(wrist, landmarks[16]),
                        self.gesture.calculate_distance(wrist, landmarks[20])
                    ]
                    avg_dist = sum(distances) / len(distances)
                    
                    # Status text
                    if is_grabbing:
                        status = "FIST DETECTED - ROTATING"
                        color = (0, 255, 255)
                    elif is_pinching:
                        status = "PINCH DETECTED - MOVING"
                        color = (0, 255, 0)
                    else:
                        status = "OPEN HAND"
                        color = (100, 100, 255)
                    
                    cv2.putText(frame, f"{status}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    
                    # Show finger distance for debugging
                    cv2.putText(frame, f"Finger Distance: {avg_dist:.3f} (Fist < 0.18)", 
                               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                    
                    # Show orientation when grabbing
                    if is_grabbing:
                        cv2.putText(frame, f"P:{hand_3d_orientation['pitch']:.0f}° R:{hand_3d_orientation['roll']:.0f}° Y:{hand_3d_orientation['yaw']:.0f}°", 
                                   (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            else:
                # No hand detected
                self.control_data['latest'] = None
                
                if self.show_camera:
                    cv2.putText(frame, "No hand detected", (w//2 - 100, h//2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Show camera feed (optional)
            if self.show_camera:
                cv2.imshow('Hand Tracking', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.running = False
                    break
        
        # Cleanup
        cap.release()
        if self.show_camera:
            cv2.destroyAllWindows()
        self.tracker.close()


def run_with_3d():
    """Run hand tracking with Panda3D visualization."""
    from visuals_3d import run_3d_app
    
    # Shared control data between threads
    control_data = {
        'latest': None
    }
    
    # Start tracking thread
    tracking = TrackingThread(control_data)
    tracking.show_camera = True  # Set False to hide camera window
    tracking.start()
    
    # Run Panda3D in main thread (required for proper rendering)
    print("Starting Panda3D 3D visualization...")
    run_3d_app(control_data)
    
    # Cleanup
    tracking.stop()


if __name__ == "__main__":
    import sys
    
    print("=== HAND-CONTROLLED 3D INTERFACE ===")
    print()
    print("This will open two windows:")
    print("  1. Camera feed with hand tracking")
    print("  2. Panda3D 3D view with controllable object")
    print()
    print("Instructions:")
    print("  - Show your hand to the camera")
    print("  - Pinch to grab the 3D object")
    print("  - Move your hand to move the object")
    print("  - Adjust pinch strength to scale the object")
    print("  - Release to hold position")
    print()
    print("Press Ctrl+C to quit")
    print()
    
    try:
        run_with_3d()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
