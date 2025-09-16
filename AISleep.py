import sys
import cv2
import time
import os
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap, QFont
from gtts import gTTS
import threading
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import pygame

class SleepDetector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("កម្មវិធីការពារការដេកក្នុងថ្នាក់រៀន")
        self.resize(800, 600)
        
        
        pygame.mixer.init()
        
        
        self.video_label = QLabel("រូបភាពពីកាមេរ៉ា")
        self.status_label = QLabel("ស្ថានភាព: កំពុងត្រួតពិនិត្យ...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        
        khmer_ui_font = QFont("Khmer OS Battambang", 14)
        self.status_label.setFont(khmer_ui_font)
        
        self.start_button = QPushButton("ចាប់ផ្តើមកាមេរ៉ា")
        self.start_button.setFont(khmer_ui_font)
        self.start_button.clicked.connect(self.start_camera)
        
        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.start_button)
        self.setLayout(layout)
        
        
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
       
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
        
        self.last_eye_time = time.time()
        self.alarm_playing = False
        
        
        self.alarm_file = "alarm.mp3"
        if not os.path.exists(self.alarm_file):
            
            tts = gTTS("សូមប្រុងប្រយ័ត្ន! សិស្សឈ្មោះ ឈឺន សុកសីហា កំពុងដេកក្នុងថ្នាក់រៀន", lang="km")
            tts.save(self.alarm_file)
            print("បានបង្កើតឯកសារសំលេងជូនដំណឹងជាភាសាខ្មែរ")
        
        
        self.khmer_font_paths = [
            "KhmerOSbattambang.ttf",
            "Khmer OS Battambang.ttf",
            "KhmerOS.ttf",
            "Dhamma.ttf",
            "/System/Library/Fonts/Supplemental/Khmer Sangam MN.ttf",
            "/System/Library/Fonts/Khmer Sangam MN.ttf"
        ]
        self.khmer_font = None
        
        for font_path in self.khmer_font_paths:
            try:
                if os.path.exists(font_path):
                    self.khmer_font = ImageFont.truetype(font_path, 50)
                    print(f"បានផ្ទុកពុម្ពអក្សរខ្មែរ: {font_path}")
                    break
            except Exception as e:
                print(f"មិនអាចផ្ទុកពុម្ពអក្សរ {font_path}: {e}")
                continue
        
        if self.khmer_font is None:
            print("ព្រមាន: រកមិនឃើញពុម្ពអក្សរខ្មែរ។ កំពុងប្រើពុម្ពអក្សរលំនាំដើម")
            self.khmer_font = ImageFont.load_default()

    def start_camera(self):
        self.cap = cv2.VideoCapture(0)  # webcam
        if not self.cap.isOpened():
            print("មិនអាចបើកកាមេរ៉ាបានទេ")
            return
        self.timer.start(30)

    def play_alarm(self):
        if not self.alarm_playing:
            self.alarm_playing = True
            threading.Thread(target=self._play_sound).start()

    def _play_sound(self):
        try:
            if os.path.exists(self.alarm_file) and os.path.getsize(self.alarm_file) > 0:
                pygame.mixer.music.load(self.alarm_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                print("បានចាក់សំលេងជូនដំណឹងដោយជោគជ័យ")
            else:
                print("ឯកសារសំលេងមិនមានឬទទេ")
        except Exception as e:
            print(f"កំហុសពេលចាក់សំលេង: {e}")
        finally:
            self.alarm_playing = False

    def put_khmer_text(self, frame, text, position, color=(255, 0, 0), font_size=50):
        """ Draw Khmer text on frame using PIL with proper font handling """
        
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
       
        try:
            if self.khmer_font:
                
                text_bbox = draw.textbbox(position, text, font=self.khmer_font)
                draw.rectangle(text_bbox, fill=(0, 0, 0))
                draw.text(position, text, font=self.khmer_font, fill=color)
                print(f"បានគូរអត្ថបទខ្មែរ: {text}")
            else:
                
                font = ImageFont.load_default()
                draw.text(position, text, font=font, fill=color)
                print("បានគូរអត្ថបទជាមួយពុម្ពអក្សរលំនាំដើម")
        except Exception as e:
            print(f"កំហុសពេលគូរអត្ថបទ: {e}")
            
            try:
                cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                print("បានគូរអត្ថបទជាមួយ OpenCV (fallback)")
            except Exception as e2:
                print(f"កំហុសពេលគូរអត្ថបទជាមួយ OpenCV: {e2}")
        
        
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            print("មិនអាចទាញយករូបភាពពីកាមេរ៉ាបានទេ")
            return
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        sleeping = False
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray)
            
            
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            if len(eyes) == 0:  
                if time.time() - self.last_eye_time > 3:  
                    sleeping = True
            else:
                self.last_eye_time = time.time()
        
        if sleeping:
            self.status_label.setText("⚠️ សូមប្រុងប្រយ័ត្ន! សិស្សកំពុងដេកក្នុងថ្នាក់រៀន!")
            self.play_alarm()
          
            frame = self.put_khmer_text(frame, "⚠️ សូមប្រុងប្រយ័ត្ន! សិស្សកំពុងដេក", (50, 50), (255, 0, 0), 50)
        else:
            self.status_label.setText("✅ សិស្សកំពុងរៀនជាធម្មតា")
            frame = self.put_khmer_text(frame, "✅ សិស្សកំពុងរៀនជាធម្មតា", (50, 50), (0, 200, 0), 50)

        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        img = QImage(rgb_frame.data, w, h, ch*w, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(img))

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        pygame.mixer.quit()  
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SleepDetector()
    window.show()
    sys.exit(app.exec())