import os
import time
import cv2
import numpy as np
import requests
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import deque
from PIL import Image, ImageTk
import mss

# --- Configuration ---
SERVER_URL = "http://localhost:8000/analyze"
CONFIDENCE_THRESHOLD = 0.90
TEMPORAL_BUFFER_SIZE = 5  # Analyze last N frames
SCAN_INTERVAL = 0.5       # Seconds between screen scans

# --- Theme Configuration ---
COLOR_BG = "#1e1e1e"
COLOR_FG = "#ffffff"
COLOR_ACCENT = "#007acc"
COLOR_DANGER = "#e51400"
COLOR_SUCCESS = "#60a917"
FONT_MAIN = ("Segoe UI", 10)
FONT_HEADER = ("Segoe UI", 16, "bold")

class ToastNotification:
    """A small, non-intrusive popup notification."""
    def __init__(self, title, message, color):
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.config(bg=color)
        
        # Geometry: Bottom Right Corner
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w, h = 300, 80
        x = screen_w - w - 20
        y = screen_h - h - 60
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        # Content
        tk.Label(self.root, text=title, font=("Segoe UI", 12, "bold"), bg=color, fg="white", anchor="w").pack(fill="x", padx=10, pady=(10, 2))
        tk.Label(self.root, text=message, font=("Segoe UI", 10), bg=color, fg="white", anchor="w").pack(fill="x", padx=10)
        
        # Auto close
        self.root.after(4000, self.destroy)
        
        # Close on click
        self.root.bind("<Button-1>", lambda e: self.destroy())

    def destroy(self):
        try:
            self.root.destroy()
        except:
            pass

class DeepfakeGuardianApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Deepfake Guardian")
        self.root.geometry("500x400")
        self.root.configure(bg=COLOR_BG)
        self.root.resizable(False, False)
        
        self.server_url = tk.StringVar(value=SERVER_URL)
        self.is_guard_active = False
        self.history = deque(maxlen=TEMPORAL_BUFFER_SIZE)
        
        self.setup_ui()
        
    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=COLOR_BG)
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_FG, font=FONT_MAIN)
        style.configure("TButton", font=FONT_MAIN, padding=6)
        style.configure("Header.TLabel", font=FONT_HEADER, background=COLOR_BG, foreground=COLOR_ACCENT)
        style.configure("Status.TLabel", background=COLOR_BG, foreground="#888888", font=("Segoe UI", 9))

        # --- Header ---
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=20, pady=20)
        
        icon_label = ttk.Label(header_frame, text="🛡️", font=("Segoe UI", 30))
        icon_label.pack(side="left", padx=(0, 10))
        
        title_label = ttk.Label(header_frame, text="Deepfake Guardian", style="Header.TLabel")
        title_label.pack(side="left", fill="y")
        
        # --- Main Controls ---
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill="both", expand=True, padx=20)
        
        # Live Guard Section
        self.guard_btn = tk.Button(content_frame, text="🛡️ START LIVE GUARD", font=("Segoe UI", 11, "bold"), 
                                   bg=COLOR_ACCENT, fg="white", activebackground="#005f9e", activeforeground="white",
                                   command=self.toggle_guard, relief="flat", padx=20, pady=10)
        self.guard_btn.pack(fill="x", pady=(10, 5))
        
        self.status_label = ttk.Label(content_frame, text="System: IDLE", style="Status.TLabel")
        self.status_label.pack(anchor="w", padx=5)
        
        ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=20)
        
        # File Scan Section
        scan_label = ttk.Label(content_frame, text="Analyze Recorded Meetings (MP4)", font=("Segoe UI", 11, "bold"))
        scan_label.pack(anchor="w", pady=(0, 10))
        
        scan_btn = tk.Button(content_frame, text="📂 SCAN VIDEO FILE", font=("Segoe UI", 10),
                             bg="#333333", fg="white", activebackground="#444444", activeforeground="white",
                             command=self.scan_video_file, relief="flat", padx=20, pady=8)
        scan_btn.pack(fill="x")

        # Settings Link
        settings_frame = ttk.Frame(self.root)
        settings_frame.pack(side="bottom", fill="x", padx=20, pady=10)
        
        tk.Label(settings_frame, text=f"Server: {self.server_url.get()}", bg=COLOR_BG, fg="#666666", font=("Segoe UI", 8)).pack(side="left")

    def toggle_guard(self):
        if self.is_guard_active:
            # STOP
            self.is_guard_active = False
            self.guard_btn.config(text="🛡️ START LIVE GUARD", bg=COLOR_ACCENT)
            self.status_label.config(text="System: IDLE", foreground="#888888")
        else:
            # START
            self.is_guard_active = True
            self.guard_btn.config(text="🛑 STOP LIVE GUARD", bg=COLOR_DANGER)
            self.status_label.config(text="System: MONITORING (Zoom/Teams/Screen)", foreground=COLOR_SUCCESS)
            
            # Start Monitor Thread
            t = threading.Thread(target=self.guard_loop, daemon=True)
            t.start()
            
    def guard_loop(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            while self.is_guard_active:
                try:
                    # Capture
                    screenshot = sct.grab(monitor)
                    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Analyze
                    result = self.analyze_frame(frame)
                    
                    # Alert Logic
                    if result:
                        self.process_live_result(result)
                        
                    time.sleep(SCAN_INTERVAL)
                except Exception as e:
                    print(f"Error: {e}")
                    time.sleep(1)

    def process_live_result(self, result):
        label = result.get("label", "unknown")
        # Temporal smoothing
        if label == "fake":
            self.history.append(1)
        elif label == "real":
            self.history.append(0)
            
        # Check alarm
        if sum(self.history) >= (self.history.maxlen * 0.8): # 80% confidence
             # Only show toast if not already showing recently? 
             # For now, simplistic check
             self.root.after(0, lambda: ToastNotification(
                 "⚠️ DEEPFAKE DETECTED", 
                 "Potential manipulation detected on screen!", 
                 COLOR_DANGER
             ))
             self.history.clear() # Reset buffer to avoid spam

    def scan_video_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov")])
        if not filepath:
            return
            
        # run in thread
        threading.Thread(target=self._run_scan, args=(filepath,), daemon=True).start()
        
    def _run_scan(self, filepath):
        self.root.after(0, lambda: messagebox.showinfo("Scanning", "Video analysis started. Check console for details."))
        
        cap = cv2.VideoCapture(filepath)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        fake_frames = 0
        analyzed_frames = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            # Sample 1 fps
            current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
            if current_frame % int(fps) != 0: continue
            
            result = self.analyze_frame(frame)
            analyzed_frames += 1
            
            if result and result.get("label") == "fake":
                fake_frames += 1
                
        cap.release()
        
        ratio = fake_frames / analyzed_frames if analyzed_frames > 0 else 0
        is_fake = ratio > 0.3
        
        msg = f"Analysis Complete.\nScore: {ratio:.1%} Probability of Deepfake."
        title = "🚨 DETECTED!" if is_fake else "✅ CLEAN"
        icon = "warning" if is_fake else "info"
        
        self.root.after(0, lambda: messagebox.showinfo(title, msg, icon=icon))

    def analyze_frame(self, frame_cv2):
        try:
            _, img_encoded = cv2.imencode('.jpg', frame_cv2)
            files = {'file': ('frame.jpg', img_encoded.tobytes(), 'image/jpeg')}
            response = requests.post(self.server_url.get(), files=files, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                return {"label": data.get("result"), "confidence": data.get("score", 0)/100}
        except:
            pass
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = DeepfakeGuardianApp(root)
    root.mainloop()
