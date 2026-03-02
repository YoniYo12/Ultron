import math
import numpy as np


class GestureRecognizer:
    """Recognize hand gestures from MediaPipe landmarks."""
    
    # Landmark indices
    WRIST = 0
    THUMB_TIP = 4
    INDEX_TIP = 8
    MIDDLE_TIP = 12
    RING_TIP = 16
    PINKY_TIP = 20
    
    def __init__(self, pinch_threshold=0.05):
        """
        Initialize gesture recognizer.
        
        Args:
            pinch_threshold: Distance threshold for pinch detection (normalized 0-1)
        """
        self.pinch_threshold = pinch_threshold
        
    def calculate_distance(self, landmark1, landmark2):
        """
        Calculate Euclidean distance between two landmarks.
        
        Args:
            landmark1: First landmark with x, y, z attributes
            landmark2: Second landmark with x, y, z attributes
            
        Returns:
            float: Distance between landmarks
        """
        dx = landmark1.x - landmark2.x
        dy = landmark1.y - landmark2.y
        dz = landmark1.z - landmark2.z
        
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def get_pinch_distance(self, hand_landmarks):
        """
        Calculate distance between thumb tip and index finger tip.
        
        Args:
            hand_landmarks: List of 21 hand landmarks
            
        Returns:
            float: Normalized distance (0-1) between thumb and index finger
        """
        thumb_tip = hand_landmarks[self.THUMB_TIP]
        index_tip = hand_landmarks[self.INDEX_TIP]
        
        return self.calculate_distance(thumb_tip, index_tip)
    
    def is_pinching(self, hand_landmarks):
        """
        Detect if hand is making a pinch gesture.
        
        Args:
            hand_landmarks: List of 21 hand landmarks
            
        Returns:
            bool: True if pinching, False otherwise
        """
        distance = self.get_pinch_distance(hand_landmarks)
        return distance < self.pinch_threshold
    
    def get_pinch_strength(self, hand_landmarks):
        """
        Get normalized pinch strength (0 = open, 1 = closed).
        
        Args:
            hand_landmarks: List of 21 hand landmarks
            
        Returns:
            float: Pinch strength from 0 (not pinching) to 1 (fully pinched)
        """
        distance = self.get_pinch_distance(hand_landmarks)
        max_distance = 0.15
        
        strength = 1.0 - min(distance / max_distance, 1.0)
        return max(0.0, strength)
    
    def is_grabbing(self, hand_landmarks):
        """
        Detect if hand is making a grab gesture (all fingers closed).
        
        Args:
            hand_landmarks: List of 21 hand landmarks
            
        Returns:
            bool: True if grabbing, False otherwise
        """
        wrist = hand_landmarks[self.WRIST]
        
        distances = [
            self.calculate_distance(wrist, hand_landmarks[self.INDEX_TIP]),
            self.calculate_distance(wrist, hand_landmarks[self.MIDDLE_TIP]),
            self.calculate_distance(wrist, hand_landmarks[self.RING_TIP]),
            self.calculate_distance(wrist, hand_landmarks[self.PINKY_TIP])
        ]
        
        avg_distance = sum(distances) / len(distances)
        return avg_distance < 0.15
    
    def is_open_palm(self, hand_landmarks):
        """
        Detect if hand is showing an open palm (all fingers extended).
        
        Args:
            hand_landmarks: List of 21 hand landmarks
            
        Returns:
            bool: True if open palm, False otherwise
        """
        wrist = hand_landmarks[self.WRIST]
        
        distances = [
            self.calculate_distance(wrist, hand_landmarks[self.INDEX_TIP]),
            self.calculate_distance(wrist, hand_landmarks[self.MIDDLE_TIP]),
            self.calculate_distance(wrist, hand_landmarks[self.RING_TIP]),
            self.calculate_distance(wrist, hand_landmarks[self.PINKY_TIP])
        ]
        
        avg_distance = sum(distances) / len(distances)
        return avg_distance > 0.25
    
    def is_pointing(self, hand_landmarks):
        """
        Detect if hand is pointing (index finger extended, others closed).
        
        Args:
            hand_landmarks: List of 21 hand landmarks
            
        Returns:
            bool: True if pointing, False otherwise
        """
        wrist = hand_landmarks[self.WRIST]
        
        index_extended = self.calculate_distance(wrist, hand_landmarks[self.INDEX_TIP]) > 0.20
        middle_closed = self.calculate_distance(wrist, hand_landmarks[self.MIDDLE_TIP]) < 0.15
        ring_closed = self.calculate_distance(wrist, hand_landmarks[self.RING_TIP]) < 0.15
        
        return index_extended and middle_closed and ring_closed
    
    def get_hand_center(self, hand_landmarks):
        """
        Calculate the center point of the hand.
        
        Args:
            hand_landmarks: List of 21 hand landmarks
            
        Returns:
            tuple: (x, y, z) coordinates of hand center
        """
        x = sum(lm.x for lm in hand_landmarks) / len(hand_landmarks)
        y = sum(lm.y for lm in hand_landmarks) / len(hand_landmarks)
        z = sum(lm.z for lm in hand_landmarks) / len(hand_landmarks)
        
        return (x, y, z)
    
    def get_hand_rotation(self, hand_landmarks):
        """
        Calculate hand rotation/orientation.
        
        Args:
            hand_landmarks: List of 21 hand landmarks
            
        Returns:
            float: Rotation angle in degrees
        """
        wrist = hand_landmarks[self.WRIST]
        middle_mcp = hand_landmarks[9]
        
        dx = middle_mcp.x - wrist.x
        dy = middle_mcp.y - wrist.y
        
        angle = math.degrees(math.atan2(dy, dx))
        return angle
    
    def get_two_hand_distance(self, hand1_landmarks, hand2_landmarks):
        """
        Calculate distance between two hands.
        
        Args:
            hand1_landmarks: First hand landmarks
            hand2_landmarks: Second hand landmarks
            
        Returns:
            float: Distance between hand centers
        """
        center1 = self.get_hand_center(hand1_landmarks)
        center2 = self.get_hand_center(hand2_landmarks)
        
        dx = center1[0] - center2[0]
        dy = center1[1] - center2[1]
        dz = center1[2] - center2[2]
        
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def both_hands_pinching(self, hand1_landmarks, hand2_landmarks):
        """
        Check if both hands are pinching (two-hand control mode).
        
        Args:
            hand1_landmarks: First hand landmarks
            hand2_landmarks: Second hand landmarks
            
        Returns:
            bool: True if both hands are pinching
        """
        return self.is_pinching(hand1_landmarks) and self.is_pinching(hand2_landmarks)
    
    def get_two_hand_center(self, hand1_landmarks, hand2_landmarks):
        """
        Get the midpoint between two hands.
        
        Args:
            hand1_landmarks: First hand landmarks
            hand2_landmarks: Second hand landmarks
            
        Returns:
            tuple: (x, y, z) midpoint between hands
        """
        center1 = self.get_hand_center(hand1_landmarks)
        center2 = self.get_hand_center(hand2_landmarks)
        
        return (
            (center1[0] + center2[0]) / 2,
            (center1[1] + center2[1]) / 2,
            (center1[2] + center2[2]) / 2
        )


if __name__ == "__main__":
    import cv2
    from hand_tracking import HandTracker
    
    cap = cv2.VideoCapture(0)
    tracker = HandTracker()
    gesture = GestureRecognizer(pinch_threshold=0.05)
    
    print("Gesture Detection Started! Press 'q' to quit.")
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        frame = cv2.flip(frame, 1)
        tracker.process_frame(frame)
        frame = tracker.draw_landmarks(frame)
        
        hands_info = tracker.get_hand_info()
        
        for idx, hand in enumerate(hands_info):
            landmarks = hand['landmarks']
            handedness = hand['handedness']
            
            pinch_distance = gesture.get_pinch_distance(landmarks)
            is_pinching = gesture.is_pinching(landmarks)
            pinch_strength = gesture.get_pinch_strength(landmarks)
            is_grabbing = gesture.is_grabbing(landmarks)
            is_open = gesture.is_open_palm(landmarks)
            
            y_offset = 30 + idx * 120
            cv2.putText(frame, f"{handedness} Hand", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Pinch Dist: {pinch_distance:.3f}", 
                       (10, y_offset + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, f"Pinching: {is_pinching}", 
                       (10, y_offset + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"Strength: {pinch_strength:.2f}", 
                       (10, y_offset + 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
            
            if is_grabbing:
                cv2.putText(frame, "GRABBING", (250, y_offset + 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            if is_open:
                cv2.putText(frame, "OPEN PALM", (250, y_offset + 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow('Gesture Detection', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    tracker.close()
