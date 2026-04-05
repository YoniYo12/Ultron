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
        cap = None
        try:
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                print("ERROR: Could not open camera!")
                return
            
            print("Camera opened. Tracking hands...")
            
            while self.running and cap.isOpened():
                try:
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
                        # Use first detected hand for control
                        hand = hands_info[0]
                        landmarks = hand['landmarks']
                        
                        # Compute gesture data
                        is_pinching = self.gesture.is_pinching(landmarks)
                        raw_strength = self.gesture.get_pinch_strength(landmarks)
                        hand_center = self.gesture.get_hand_center(landmarks)
                        is_grab = self.gesture.is_grab(landmarks)
                        control = self.mapper.update(
                            is_pinching, raw_strength, hand_center, is_grab
                        )
                        
                        # Store in shared dict for 3D app
                        self.control_data['latest'] = control
                        
                        # Draw on camera feed
                        if self.show_camera:
                            frame = self.tracker.draw_landmarks(frame)
                            
                            if is_grab:
                                status = "GRAB (Rotate)"
                                color = (0, 165, 255)
                            elif is_pinching:
                                status = "PINCH (Move)"
                                color = (0, 255, 0)
                            else:
                                status = "OPEN"
                                color = (100, 100, 255)
                            
                            cv2.putText(frame, f"{hand['handedness']} Hand - {status}", 
                                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                            
                            grab_norm = getattr(self.gesture, '_last_grab_norm', 0)
                            gconf = control.get('grab_confidence', 0)
                            pinch_dist = self.gesture.get_pinch_distance(landmarks)
                            cv2.putText(
                                frame,
                                f"Grab norm: {grab_norm:.2f}  conf: {gconf:.2f}  pinch: {pinch_dist:.3f}",
                                (10, 65),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                (200, 200, 200),
                                2,
                            )
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
                            
                except Exception as e:
                    # Silently continue on frame processing errors
                    pass
                    
        except Exception as e:
            print(f"Tracking error: {e}")
        finally:
            # Cleanup
            if cap is not None:
                cap.release()
            if self.show_camera:
                try:
                    cv2.destroyAllWindows()
                except:
                    pass
            try:
                self.tracker.close()
            except:
                pass


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
    
    try:
        # Run Panda3D in main thread (required for proper rendering)
        print("Starting Panda3D 3D visualization...")
        run_3d_app(control_data)
    finally:
        # Always cleanup, even if there's an error
        print("Shutting down tracking thread...")
        tracking.stop()
        print("Cleanup complete!")


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