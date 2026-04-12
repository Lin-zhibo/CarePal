import math
import numpy as np

# COCO keypoint indices
NOSE = 0
LEFT_EYE = 1
RIGHT_EYE = 2
LEFT_EAR = 3
RIGHT_EAR = 4
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_KNEE = 13
RIGHT_KNEE = 14
LEFT_ANKLE = 15
RIGHT_ANKLE = 16

"""
Function: calculate_angle
Parameters:
  v1 (tuple/list): First vector [x, y].
  v2 (tuple/list): Second vector [x, y].
Return: 
  float: The angle between the two vectors in degrees.
Description: Calculates the angle between two 2D vectors using the dot product and acos.
"""
def calculate_angle(v1, v2):
    # Calculate dot product
    dot_product = v1[0] * v2[0] + v1[1] * v2[1]
    # Calculate magnitudes
    mag_v1 = math.sqrt(v1[0]**2 + v1[1]**2)
    mag_v2 = math.sqrt(v2[0]**2 + v2[1]**2)
    
    if mag_v1 == 0 or mag_v2 == 0:
        return 0.0
        
    cos_theta = dot_product / (mag_v1 * mag_v2)
    # Clamp cos_theta to avoid floating point inaccuracies causing domain errors
    cos_theta = max(min(cos_theta, 1.0), -1.0)
    
    return math.degrees(math.acos(cos_theta))

"""
Function: get_valid_point
Parameters:
  kp_list (list/ndarray): Full array of 17 keypoints [17, 2] or [17, 3].
  idx1 (int): The primary keypoint index.
  idx2 (int): The fallback keypoint index.
Return: 
  tuple: A valid (x, y) point, or None if both are invalid (0, 0).
Description: Helper to get the center of two points or fallback to one of them if the other is occluded.
"""
def get_valid_point(kp_list, idx1, idx2):
    p1 = kp_list[idx1][:2]
    p2 = kp_list[idx2][:2]
    
    v1_valid = (p1[0] > 0 and p1[1] > 0)
    v2_valid = (p2[0] > 0 and p2[1] > 0)
    
    if v1_valid and v2_valid:
        return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
    elif v1_valid:
        return (p1[0], p1[1])
    elif v2_valid:
        return (p2[0], p2[1])
    else:
        return None

"""
Function: check_fall
Parameters:
  keypoints (ndarray): Array containing 17 keypoints (shape: [17, 2] or [17, 3]).
  bbox (list/ndarray): Bounding box coordinates in format [xmin, ymin, xmax, ymax].
Return: 
  tuple: (bool, str) - True if fall detected, along with the triggered condition string (e.g., "Cond3"), (False, "") otherwise.
Description: Evaluates 5 specific geometrical conditions based on body keypoints to detect if a person has fallen.
"""
def check_fall(keypoints, bbox):
    # Cond 3: Aspect ratio of bounding box
    xmin, ymin, xmax, ymax = bbox
    width = xmax - xmin
    height = ymax - ymin
    
    # Check if all keypoints are valid (not occluded)
    all_valid = all(kp[0] > 0 and kp[1] > 0 for kp in keypoints)
    
    if all_valid and height > 0:
        aspect_ratio = float(width) / float(height)
        if aspect_ratio > 0.90:
            return True, "Cond3(AspectRatio>0.9)"

    # Check keypoint availability
    l_sh = keypoints[LEFT_SHOULDER][:2]
    r_sh = keypoints[RIGHT_SHOULDER][:2]
    l_knee = keypoints[LEFT_KNEE][:2]
    r_knee = keypoints[RIGHT_KNEE][:2]
    
    sh_valid = (l_sh[0] > 0 and l_sh[1] > 0) and (r_sh[0] > 0 and r_sh[1] > 0)
    knee_valid = (l_knee[0] > 0 and l_knee[1] > 0) and (r_knee[0] > 0 and r_knee[1] > 0)
    
    c_ankle = get_valid_point(keypoints, LEFT_ANKLE, RIGHT_ANKLE)
    c_hip = get_valid_point(keypoints, LEFT_HIP, RIGHT_HIP)
    c_sh = get_valid_point(keypoints, LEFT_SHOULDER, RIGHT_SHOULDER)
    c_knee = get_valid_point(keypoints, LEFT_KNEE, RIGHT_KNEE)

    # Cond 1: Shoulder y vs Ankle y
    if sh_valid and c_ankle is not None:
        min_shoulder_y = min(l_sh[1], r_sh[1])
        if min_shoulder_y >= c_ankle[1]:
            return True, "Cond1(Shoulder>=Ankle)"

    # Cond 2: Shoulder y vs Knee y
    if sh_valid and knee_valid:
        max_shoulder_y = max(l_sh[1], r_sh[1])
        min_knee_y = min(l_knee[1], r_knee[1])
        if max_shoulder_y > min_knee_y:
            return True, "Cond2(Shoulder>Knee)"

    # Cond 4: Knee-Hip vector angle to the ground (x-axis)
    if c_hip is not None and knee_valid:
        # Calculate angle of line to ground using atan2 (hip to knee)
        theta1 = math.degrees(math.atan2(l_knee[1] - c_hip[1], l_knee[0] - c_hip[0]))
        theta2 = math.degrees(math.atan2(r_knee[1] - c_hip[1], r_knee[0] - c_hip[0]))
        
        abs_t1 = abs(theta1)
        abs_t2 = abs(theta2)
        
        min_theta = min(abs_t1, abs_t2)
        max_theta = max(abs_t1, abs_t2)
        
        if min_theta < 30.0 and max_theta < 70.0:
            return True, "Cond4(KneeHipAngle)"

    # Cond 5: Body joint vector angles
    if c_sh is not None and c_hip is not None and c_knee is not None and c_ankle is not None:
        v1 = [c_sh[0] - c_hip[0], c_sh[1] - c_hip[1]]
        v2 = [c_knee[0] - c_hip[0], c_knee[1] - c_hip[1]]
        v3 = [c_hip[0] - c_knee[0], c_hip[1] - c_knee[1]]
        v4 = [c_ankle[0] - c_knee[0], c_ankle[1] - c_knee[1]]
        
        theta3 = calculate_angle(v1, v2)
        theta4 = calculate_angle(v3, v4)
        
        if theta3 < 70.0 and theta4 < 30.0:
            return True, "Cond5(JointAngles)"

    return False, ""