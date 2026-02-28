import cv2
import mediapipe as mp
import numpy as np
import urllib.request
import os

class HandTracker:
    def __init__(self):
        """Initialize MediaPipe hand tracking using tasks API for Python 3.13."""
        self.mp_image = mp.Image
        self.mp_image_format = mp.ImageFormat
        
        model_path = 'hand_landmarker.task'
        if not os.path.exists(model_path):
            print("Downloading hand landmarker model...")
            url = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
            urllib.request.urlretrieve(url, model_path)
            print("Model downloaded!")
        
        base_options = mp.tasks.BaseOptions(model_asset_path=model_path)
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self.results = None
        self.timestamp_ms = 0
    
    def process_frame(self, frame):
        """Process a frame and detect hands."""
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        self.timestamp_ms += 33
        self.results = self.landmarker.detect_for_video(mp_image, self.timestamp_ms)
        
        return frame
    
    def get_hand_landmarks(self):
        """Get hand landmarks from the last processed frame."""
        if self.results and self.results.hand_landmarks:
            return self.results.hand_landmarks
        return None
    
    def get_hand_info(self):
        """Get detailed hand information including handedness."""
        if not self.results or not self.results.hand_landmarks:
            return []
        
        hands_info = []
        for idx, hand_landmarks in enumerate(self.results.hand_landmarks):
            handedness = self.results.handedness[idx][0]
            hands_info.append({
                'landmarks': hand_landmarks,
                'handedness': handedness.category_name,
                'score': handedness.score
            })
        
        return hands_info
    
    def draw_landmarks(self, frame):
        """Draw hand landmarks and connections on the frame."""
        if not self.results or not self.results.hand_landmarks:
            return frame
        
        HAND_CONNECTIONS = [
            (0, 1), (1, 2), (2, 3), (3, 4),
            (0, 5), (5, 6), (6, 7), (7, 8),
            (0, 9), (9, 10), (10, 11), (11, 12),
            (0, 13), (13, 14), (14, 15), (15, 16),
            (0, 17), (17, 18), (18, 19), (19, 20),
            (5, 9), (9, 13), (13, 17)
        ]
        
        h, w, _ = frame.shape
        
        for hand_landmarks in self.results.hand_landmarks:
            for connection in HAND_CONNECTIONS:
                start_idx, end_idx = connection
                start = hand_landmarks[start_idx]
                end = hand_landmarks[end_idx]
                
                start_point = (int(start.x * w), int(start.y * h))
                end_point = (int(end.x * w), int(end.y * h))
                
                cv2.line(frame, start_point, end_point, (0, 255, 0), 2)
            
            for landmark in hand_landmarks:
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                cv2.circle(frame, (x, y), 5, (255, 0, 255), -1)
        
        return frame
    
    def get_landmark_positions(self, frame_width, frame_height):
        """Get landmark positions in pixel coordinates."""
        if not self.results or not self.results.hand_landmarks:
            return []
        
        hands_positions = []
        for hand_landmarks in self.results.hand_landmarks:
            landmarks = []
            for landmark in hand_landmarks:
                x = int(landmark.x * frame_width)
                y = int(landmark.y * frame_height)
                z = landmark.z
                landmarks.append((x, y, z))
            hands_positions.append(landmarks)
        
        return hands_positions
    
    def close(self):
        """Clean up resources."""
        self.landmarker.close()


if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    tracker = HandTracker()
    
    print("Hand Tracking Started! Press 'q' to quit.")
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Failed to capture frame")
            break
        
        frame = cv2.flip(frame, 1)
        
        tracker.process_frame(frame)
        frame = tracker.draw_landmarks(frame)
        
        hands_info = tracker.get_hand_info()
        for idx, hand in enumerate(hands_info):
            cv2.putText(frame, f"{hand['handedness']} Hand", 
                       (10, 30 + idx * 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       1, (0, 255, 0), 2)
        
        cv2.imshow('Hand Tracking', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    tracker.close()