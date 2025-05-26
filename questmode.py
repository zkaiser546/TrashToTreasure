from kivy.uix.checkbox import CheckBox
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.properties import NumericProperty, StringProperty, ListProperty
from kivy.graphics.texture import Texture
import cv2
import requests
import base64
import time
import json


class QuestGameScreen(Screen):
    timer = NumericProperty(60)
    detected_image_name = StringProperty("")
    user_feedback = StringProperty("")
    detected_text = StringProperty("Press START to begin detection")
    level = NumericProperty(1)
    current_target = StringProperty("")
    coins = NumericProperty(0)
    feedback_color = ListProperty([0, 1, 0, 1])
    targets_completed = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capture = None
        self.current_camera_index = 0
        self.tracker = None
        self.tracking = False
        self.selected_label = ""
        self.awaiting_choice = False
        self.feedback_time = 0
        self.timer_event = None

        # Roboflow API configuration
        self.roboflow_api_key = "EOTI0reGUeEwnGjkUTE7"  # From your screenshot
        self.model_name = "trash-detection-2-4oj4h"
        self.model_version = "3"

        # Enhanced level progression system
        self.level_targets = {
            1: {
                "targets": ["clear plastic bottle", "glass bottle"],
                "time": 60,
                "reward": 10
            },
            2: {
                "targets": ["drink can", "food can"],
                "time": 55,
                "reward": 15
            },
            3: {
                "targets": ["paper", "cardboard"],
                "time": 50,
                "reward": 20
            },
            4: {
                "targets": ["plastic film", "plastic utensils"],
                "time": 45,
                "reward": 25
            },
            5: {
                "targets": ["glass jar", "metal lid"],
                "time": 40,
                "reward": 30
            },
            6: {
                "targets": ["crisp packet", "wrapper"],
                "time": 35,
                "reward": 35
            },
            7: {
                "targets": ["foam cup", "styrofoam piece"],
                "time": 30,
                "reward": 40
            },
            8: {
                "targets": ["battery", "electronic waste"],
                "time": 25,
                "reward": 45
            },
            9: {
                "targets": ["food waste", "biodegradable"],
                "time": 20,
                "reward": 50
            },
            10: {
                "targets": ["mixed waste", "unlabeled litter"],
                "time": 15,
                "reward": 100
            }
        }

        # Comprehensive classification system
        self.class_map = {
            # Recyclable
            "clear plastic bottle": "recyclable",
            "glass bottle": "recyclable",
            "drink can": "recyclable",
            "food can": "recyclable",
            "paper": "recyclable",
            "cardboard": "recyclable",
            "glass jar": "recyclable",
            "metal lid": "recyclable",

            # Non-recyclable
            "plastic film": "non-recyclable",
            "plastic utensils": "non-recyclable",
            "crisp packet": "non-recyclable",
            "wrapper": "non-recyclable",
            "foam cup": "non-recyclable",
            "styrofoam piece": "non-recyclable",

            # Hazardous
            "battery": "hazardous",
            "electronic waste": "hazardous",

            # Biodegradable
            "food waste": "biodegradable",

            # Miscellaneous
            "mixed waste": "non-recyclable",
            "unlabeled litter": "non-recyclable"
        }

        # Initialize first level
        self.current_target = self.level_targets[1]["targets"][0]
        self.update_level_info()

    def start_camera(self):
        if not self.capture or not self.capture.isOpened():
            self.capture = cv2.VideoCapture(self.current_camera_index)
            if not self.capture.isOpened():
                self.detected_text = "Error: Unable to access camera"
                return
            Clock.schedule_interval(self.update_frame, 1.0 / 30.0)
            self.detected_text = "Detecting..."
            self.start_timer()
            self.update_level_info()

    def stop_camera(self):
        if self.capture and self.capture.isOpened():
            self.capture.release()
        Clock.unschedule(self.update_frame)
        if self.timer_event:
            self.timer_event.cancel()
        self.detected_text = "Camera stopped"

    def switch_camera(self):
        self.current_camera_index = 1 - self.current_camera_index
        if self.capture:
            self.capture.release()
        self.start_camera()
        self.reset_tracking()

    def detect_with_roboflow(self, frame):
        # Resize frame for better performance
        frame = cv2.resize(frame, (640, 480))

        # Convert frame to JPEG
        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            print("Failed to encode image")
            return None

        img_str = base64.b64encode(buffer).decode('utf-8')

        # Prepare API request
        url = f"https://detect.roboflow.com/{self.model_name}/{self.model_version}"
        params = {
            "api_key": self.roboflow_api_key,
            "confidence": 50,
            "format": "json"
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            response = requests.post(
                url,
                params=params,
                headers=headers,
                data=img_str,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return None

    def update_frame(self, dt):
        ret, frame = self.capture.read()
        if not ret:
            return

        current_time = time.time()

        # Tracking existing object
        if self.tracking and self.tracker:
            success, bbox = self.tracker.update(frame)
            if success:
                x, y, w, h = map(int, bbox)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            else:
                self.reset_tracking()

        # Detect new objects
        if not self.tracking and not self.awaiting_choice and (current_time - self.feedback_time > 2):
            results = self.detect_with_roboflow(frame)

            if results and 'predictions' in results:
                for pred in results['predictions']:
                    label = pred['class'].lower()
                    current_targets = self.level_targets[self.level]["targets"]

                    if label not in current_targets:
                        continue

                    x1 = int(pred['x'] - pred['width'] / 2)
                    y1 = int(pred['y'] - pred['height'] / 2)
                    x2 = int(pred['x'] + pred['width'] / 2)
                    y2 = int(pred['y'] + pred['height'] / 2)

                    # Initialize tracker
                    self.tracker = cv2.legacy.TrackerKCF_create()
                    if self.tracker.init(frame, (x1, y1, x2 - x1, y2 - y1)):
                        self.tracking = True
                        self.awaiting_choice = True
                        self.selected_label = label
                        self.detected_text = f"Detected: {label}"
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    break

        # Display frame
        frame = cv2.flip(frame, 0)
        buf = frame.tostring()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.ids.hunt_image.texture = texture

    def check_answer(self):
        selected = None
        for box in self.ids.classification_container.children:
            for child in box.children:
                if isinstance(child, CheckBox) and child.active:
                    selected = child.category
                    break
            if selected:
                break

        if selected and self.awaiting_choice:
            detected_obj = self.selected_label.lower()
            correct_category = self.class_map.get(detected_obj, "")

            if selected == correct_category:
                reward = self.level_targets[self.level]["reward"]
                self.user_feedback = f"Correct! +{reward} coins"
                self.coins += reward
                self.feedback_color = [0, 1, 0, 1]
                self.targets_completed += 1
                self.next_target()
            else:
                self.user_feedback = f"Wrong! {detected_obj} is {correct_category}"
                self.feedback_color = [1, 0, 0, 1]

            self.feedback_time = time.time()
            self.reset_tracking()
            Clock.schedule_once(lambda dt: setattr(self, 'user_feedback', ""), 2)
            Clock.schedule_once(lambda dt: setattr(self, 'feedback_color', [0, 1, 0, 1]), 2)

    def next_target(self):
        current_targets = self.level_targets[self.level]["targets"]

        # Check if all targets completed
        if self.targets_completed >= len(current_targets):
            self.next_level()
            return

        # Move to next target in level
        current_index = current_targets.index(self.current_target)
        if current_index + 1 < len(current_targets):
            self.current_target = current_targets[current_index + 1]
        self.update_level_info()

    def next_level(self):
        if self.level < len(self.level_targets):
            self.level += 1
            self.targets_completed = 0
            self.current_target = self.level_targets[self.level]["targets"][0]
            self.update_level_info()
            self.coins += self.level * 20  # Level completion bonus
            self.start_timer()  # Reset timer with new level time
        else:
            self.user_feedback = "Congratulations! You completed all levels!"
            self.stop_camera()

    def update_level_info(self):
        if hasattr(self, 'ids'):
            targets = ", ".join(self.level_targets[self.level]["targets"])
            self.ids.level_label.text = f"Level {self.level}: Find {targets}"
            self.ids.target_label.text = f"Current: {self.current_target}"
            self.ids.progress_label.text = f"Progress: {self.targets_completed}/{len(self.level_targets[self.level]['targets'])}"

    def start_timer(self):
        if self.timer_event:
            self.timer_event.cancel()
        self.timer = self.level_targets[self.level]["time"]
        self.timer_event = Clock.schedule_interval(self.update_timer, 1)

    def update_timer(self, dt):
        if self.timer > 0:
            self.timer -= 1
            mins = self.timer // 60
            secs = self.timer % 60
            self.ids.timer_label.text = f"Time: {mins:02}:{secs:02}"
        else:
            self.timer_event.cancel()
            self.detected_text = "Time's up!"
            self.user_feedback = "Level Failed"
            self.feedback_color = [1, 0, 0, 1]
            self.stop_camera()

    def reset_tracking(self):
        self.tracking = False
        self.awaiting_choice = False
        self.selected_label = ""
        self.detected_image_name = ""
        if self.tracker:
            self.tracker = None

    def on_leave(self):
        self.stop_camera()