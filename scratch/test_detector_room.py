import os
import sys
import numpy as np
import cv2

sys.path.insert(0, r"c:\Project\plickers\scanner")
from detector import CardDetector

def run_test():
    student_map = {1: "Arun Kumar", 2: "Priya Sharma", 3: "Rahul Verma"}
    detector = CardDetector(student_map=student_map)
    
    # Create a simulated classroom photo (1280x720) with background
    frame = np.full((720, 1280, 3), 220, dtype=np.uint8)
    
    # Load ArUco dictionary
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    
    # Generate and place markers on the frame with different rotations
    markers_info = [
        (1, 0, (200, 200)),     # Card 1 at 0 deg (Answer A)
        (2, 90, (550, 250)),    # Card 2 at 90 deg CW (Answer B)
        (3, 180, (900, 220)),   # Card 3 at 180 deg (Answer C)
    ]
    
    for marker_id, rot_deg, (x, y) in markers_info:
        img_marker = cv2.aruco.generateImageMarker(dictionary, marker_id, 120)
        # Convert to 3 channel
        img_marker_bgr = cv2.cvtColor(img_marker, cv2.COLOR_GRAY2BGR)
        
        # Rotate marker image
        if rot_deg == 90:
            img_marker_bgr = cv2.rotate(img_marker_bgr, cv2.ROTATE_90_CLOCKWISE)
        elif rot_deg == 180:
            img_marker_bgr = cv2.rotate(img_marker_bgr, cv2.ROTATE_180)
        elif rot_deg == 270:
            img_marker_bgr = cv2.rotate(img_marker_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
        h, w = img_marker_bgr.shape[:2]
        frame[y:y+h, x:x+w] = img_marker_bgr
        
    results = detector.detect(frame)
    print(f"Room Photo Detections Count: {len(results)}")
    for r in results:
        print(f"Detected: Card #{r['card_id']} ({r['student_name']}) -> Answer: {r['answer']} (Rotation: {r['rotation']} deg, Conf: {r['confidence']:.1f}%)")
        
    expected = {1: "A", 2: "B", 3: "C"}
    all_matched = True
    for r in results:
        if expected.get(r["card_id"]) != r["answer"]:
            all_matched = False
            print(f"MISMATCH on Card {r['card_id']}: expected {expected.get(r['card_id'])}, got {r['answer']}")
            
    if len(results) == 3 and all_matched:
        print("\nSUCCESS: All student answers in classroom photo accurately detected!")

if __name__ == "__main__":
    run_test()
