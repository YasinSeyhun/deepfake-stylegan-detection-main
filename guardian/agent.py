import os
import time
import cv2
import numpy as np
import requests
import pyautogui
import threading
import tkinter as tk
from collections import deque
from PIL import Image

# Configuration
SERVER_URL = "http://localhost:8000/analyze"
CONFIDENCE_THRESHOLD = 0.90
TEMPORAL_BUFFER_SIZE = 5  # Analyze last N frames for consistency
SCAN_INTERVAL = 0.5       # Seconds between screen scans in Sentry Mode

class DeepfakeSentinel:
    def __init__(self):
        self.running = False
        self.root = None
        self.alert_label = None
        self.history = deque(maxlen=TEMPORAL_BUFFER_SIZE)
        self.overlay_active = False

    def create_hud(self):
        """Creates a transparent overlay for alerts (The HUD)."""
        self.root = tk.Tk()
        self.root.title("Deepfake Sentinel HUD")
        
        # Make it full screen and transparent
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        self.root.geometry(f"{width}x{height}+0+0")
        self.root.overrideredirect(True) # Remove window chrome
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.0) # Start invisible
        
        # In Windows, making it click-through requires platform specific calls, 
        # for MVP we just keep it simple or invisible when safe.
        # Ideally, we just show a border.
        
        self.canvas = tk.Canvas(self.root, width=width, height=height, highlightthickness=0)
        self.canvas.pack()
        
        # Create a red border rectangle (hidden initially)
        self.border = self.canvas.create_rectangle(0, 0, width, height, outline="red", width=10, state='hidden')
        self.text = self.canvas.create_text(width//2, 50, text="⚠️ DEEPFAKE DETECTED ⚠️", fill="red", font=("Courier", 30, "bold"), state='hidden')
        
        # Transparent background for canvas
        self.root.config(bg='white')
        self.root.attributes("-transparentcolor", "white")
        
        self.root.mainloop()

    def show_alert(self):
        if not self.root: return
        self.canvas.itemconfig(self.border, state='normal')
        self.canvas.itemconfig(self.text, state='normal')
        self.root.attributes("-alpha", 1.0)
        self.overlay_active = True

    def hide_alert(self):
        if not self.root: return
        self.canvas.itemconfig(self.border, state='hidden')
        self.canvas.itemconfig(self.text, state='hidden')
        self.root.attributes("-alpha", 0.0)
        self.overlay_active = False

    def analyze_frame(self, frame_cv2):
        """Sends a frame to the backend for analysis."""
        try:
            # Encode frame to JPEG
            _, img_encoded = cv2.imencode('.jpg', frame_cv2)
            files = {'file': ('frame.jpg', img_encoded.tobytes(), 'image/jpeg')}
            
            start = time.time()
            response = requests.post(SERVER_URL, files=files, timeout=2)
            # print(f"Latency: {time.time() - start:.2f}s")
            
            if response.status_code == 200:
                result = response.json()
                # Server returns: {"result": "fake", "score": 99.5, ...}
                label = result.get("result", "unknown").lower()
                score = result.get("score", 0.0)
                confidence = score / 100.0
                
                return {"label": label, "confidence": confidence}
            elif response.status_code == 400:
                # Likely "No face detected"
                return {"label": "no_face", "confidence": 0.0}
        except Exception as e:
            print(f"Connection Error: {e}")
        return None

    def update_temporal_logic(self, result):
        if not result: return
        
        label = result.get("label", "").lower()
        conf = result.get("confidence", 0.0)
        
        if label == "fake":
            self.history.append(1)
        elif label == "real":
            self.history.append(0)
        else:
            # No face or error, treat as neutral (or 0)
            self.history.append(0)

        # Trigger if majority of buffer is FAKE
        if sum(self.history) >= (self.history.maxlen * 0.6): # 60% agreement
             if not self.overlay_active:
                 print(">>> ALARM: Deepfake Activity Detected! <<<")
                 # We need to signal the UI thread. simpler to just print for this console version
                 # In full version, use queue to talk to Tkinter
                 
    def start_sentry_mode(self):
        """Monitors the screen continuously."""
        print("🛡️ Sentry Mode ACTIVATED. Monitoring screen...")
        print("Press Ctrl+C to stop.")
        
        # Start HUD in separate thread (Tkinter needs main thread usually, but let's try)
        # Actually Tkinter MUST be main thread. So capture loop goes to thread.
        t = threading.Thread(target=self._capture_loop)
        t.daemon = True
        t.start()
        
        self.create_hud()

    def _capture_loop(self):
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1] # Primary monitor
            
            while True:
                # Capture Screen
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                frame = np.array(img)
                # Convert RGB to BGR for OpenCV
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Analyze
                result = self.analyze_frame(frame)
                
                # Update Logic
                if result:
                    label = result.get("label", "unknown")
                    conf = result.get("confidence", 0.0)
                    print(f"Scanner: {label} ({conf:.2f})", end="\r")
                    
                    self.update_temporal_logic(result)
                    
                    # Simple direct UI update (unsafe in complex apps but might work for simple flag)
                    # Ideally use queue. For MVP:
                    is_danger = (sum(self.history) >= (self.history.maxlen * 0.6))
                    if is_danger:
                         self.root.after(0, self.show_alert)
                    else:
                         self.root.after(0, self.hide_alert)
                
                time.sleep(SCAN_INTERVAL)

    def scan_file(self, filepath):
        """Scans a video file frame by frame."""
        if not os.path.exists(filepath):
            print("File not found.")
            return

        cap = cv2.VideoCapture(filepath)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        
        print(f"Scanning video: {filepath} ({duration:.1f}s)")
        
        fake_frames = 0
        analyzed_frames = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            # Extract 1 frame per second to save time
            current_frame_id = cap.get(cv2.CAP_PROP_POS_FRAMES)
            if current_frame_id % int(fps) != 0:
                continue
                
            result = self.analyze_frame(frame)
            analyzed_frames += 1
            
            if result and result.get("label") == "fake":
                fake_frames += 1
                timestamp = current_frame_id / fps
                print(f"⚠️ Fake detected at {timestamp:.1f}s (Conf: {result['confidence']:.2f})")
        
        cap.release()
        
        if analyzed_frames > 0:
            ratio = fake_frames / analyzed_frames
            print(f"\n--- REPORT ---")
            print(f"Analyzed Frames: {analyzed_frames}")
            print(f"Fake Frames: {fake_frames}")
            print(f"Probability: {ratio:.1%}")
            if ratio > 0.3:
                print("CONCLUSION: 🚨 FAKE VIDEO DETECTED 🚨")
            else:
                print("CONCLUSION: ✅ Video appears clean")

if __name__ == "__main__":
    import sys
    sentinel = DeepfakeSentinel()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "sentry":
            sentinel.start_sentry_mode()
        elif cmd == "scan" and len(sys.argv) > 2:
            sentinel.scan_file(sys.argv[2])
        else:
            print("Usage: python agent.py [sentry | scan <file.mp4>]")
    else:
        print("Usage: python agent.py [sentry | scan <file.mp4>]")
