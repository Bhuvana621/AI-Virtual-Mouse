import cv2
import mediapipe as mp
import pyautogui
import math
import time
from tkinter import Tk, Label, StringVar
import threading
import queue


#Tkinter Status Panel
class StatusDisplay:
    def __init__(self, root, status_queue):
        self.status_queue = status_queue
        self.status_var = StringVar()
        self.status_var.set("Waiting for input...")
        
        # Create a larger label with increased padding and font size
        self.label = Label(
            root,
            textvariable=self.status_var,
            font=("Helvetica", 20),  # Increased font size
            bg="lightblue",         # Background color for better visibility
            fg="black",             # Text color
            padx=20,                # Horizontal padding
            pady=20                 # Vertical padding
        )
        self.label.pack(expand=True, fill="both", padx=20, pady=20)
        self.update_status_from_queue()

    def update_status(self, message):
        self.status_var.set(message)

    def update_status_from_queue(self):
        while not self.status_queue.empty():
            message = self.status_queue.get_nowait()
            self.update_status(message)
        # Schedule the next status check
        self.label.after(100, self.update_status_from_queue)


# AI Virtual Mouse Logic
def virtual_mouse_logic(status_queue):
    # Initialize MediaPipe Hand tracking
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    hands = mp_hands.Hands(max_num_hands=1)

    # Setup webcam capture
    cap = cv2.VideoCapture(0)

    # Get screen size for cursor movement scaling
    screen_width, screen_height = pyautogui.size()

    # Initialize gesture state variables
    copy_triggered = False
    paste_triggered = False
    paste_last_time = 0
    paste_cooldown = 2  # Cooldown in seconds for paste

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Flip the frame horizontally for a mirror effect
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert the frame to RGB for MediaPipe

        # Process the frame with MediaPipe Hand
        results = hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for landmarks in results.multi_hand_landmarks:
                # Draw the hand landmarks on the frame
                mp_drawing.draw_landmarks(frame, landmarks, mp_hands.HAND_CONNECTIONS)

                # Get positions of important landmarks
                h, w, _ = frame.shape
                index_finger_tip = landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                middle_finger_tip = landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                thumb_tip = landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                pinky_tip = landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
                ring_finger_tip = landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
                index_finger_mcp = landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
                middle_finger_mcp = landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]



                # Convert normalized positions to pixel coordinates
                index_finger_x, index_finger_y = int(index_finger_tip.x * w), int(index_finger_tip.y * h)
                middle_finger_x, middle_finger_y = int(middle_finger_tip.x * w), int(middle_finger_tip.y * h)
                thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
                pinky_x, pinky_y = int(pinky_tip.x * w), int(pinky_tip.y * h)
                ring_finger_x, ring_finger_y = int(ring_finger_tip.x * w), int(ring_finger_tip.y * h)
                index_tip_y = int(index_finger_tip.y * h)
                middle_tip_y = int(middle_finger_tip.y * h)
                index_middle_y = int((index_finger_mcp.y + index_finger_tip.y) / 2 * h)
                middle_index_y = int((middle_finger_mcp.y + middle_finger_tip.y) / 2 * h)



                # Cursor movement based on the index finger
                cursor_x = int(index_finger_x * screen_width / w)
                cursor_y = int(index_finger_y * screen_height / h)
                pyautogui.moveTo(cursor_x, cursor_y)
                status_queue.put("Mouse Moved")

                # Gesture: Click detection (Thumb and Index close)
                distance_thumb_index = math.hypot(index_finger_x - thumb_x, index_finger_y - thumb_y)
                if distance_thumb_index < 20:
                    pyautogui.click()
                    status_queue.put("Clicked")

                # Selection Gesture: Index and Middle Finger Spread Apart (More than 60 pixels)
                if distance_thumb_index > 40:
                    selection_mode = True  # Activate selection mode
                else:
                    selection_mode = False  # Deactivate selection mode


                # Gesture: Copy (Pinch Gesture: Thumb and Middle Finger close)
                distance_thumb_middle = math.hypot(middle_finger_x - thumb_x, middle_finger_y - thumb_y)
                if distance_thumb_middle < 20 and not copy_triggered:
                    pyautogui.hotkey('ctrl', 'c')
                    copy_triggered = True
                    status_queue.put("Copied")
                elif distance_thumb_middle > 20:  # Reset copy trigger when fingers are apart
                    copy_triggered = False
                    

                # Gesture: Paste (Peace Sign: Index and Middle Finger spread apart)
                distance_index_middle = math.hypot(index_finger_x - middle_finger_x, index_finger_y - middle_finger_y)
                current_time = time.time()
                if distance_index_middle > 60 and not paste_triggered and (current_time - paste_last_time > paste_cooldown):
                    pyautogui.hotkey('ctrl', 'v')
                    paste_triggered = True
                    paste_last_time = current_time
                    status_queue.put("Pasted")
                elif distance_index_middle < 50:
                    paste_triggered = False

               # Scroll detection based on index and middle finger vertical distance
                if abs(index_tip_y - middle_index_y) < 15:  # Index tip at middle of middle finger
                    pyautogui.scroll(10)  # Scroll up
                    status_queue.put("Scrolling Up")
                elif abs(middle_tip_y - index_middle_y) < 15:  # Middle tip at middle of index finger
                    pyautogui.scroll(-10)  # Scroll down
                    status_queue.put("Scrolling Down")
                  

              # Calculate the distance between thumb and pinky for volume control
                distance_thumb_pinky = math.hypot(thumb_x - pinky_x, thumb_y - pinky_y)
                distance_thumb_ring = math.hypot(thumb_x - ring_finger_x, thumb_y - ring_finger_y)

              # Volume Control Gestures
                if distance_thumb_pinky < 5:  # Increase volume gesture
                    pyautogui.press("volumeup")
                    status_queue.put("volume Increased")
                elif distance_thumb_ring < 10:  # Decrease volume gesture
                    pyautogui.press("volumedown")
                    status_queue.put("volume Decreased") 

        # Display the webcam feed
        cv2.imshow("AI Virtual Mouse", frame)

        # Exit on pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


# Run both the status panel and the virtual mouse in parallel
if __name__ == "__main__":
    root = Tk()
    root.title("Status Panel")

    # Set a larger window size
    root.geometry("400x250")  # Width x Height

    #Make the window always on top
    root.attributes('-topmost', True)

    # Create a thread-safe queue for status updates
    status_queue = queue.Queue()

    # Initialize the status display
    status_display = StatusDisplay(root, status_queue)

    # Run the virtual mouse logic in a separate thread
    threading.Thread(target=virtual_mouse_logic, args=(status_queue,), daemon=True).start()

    # Run the Tkinter mainloop in the main thread
    root.mainloop()
