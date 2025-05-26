from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock
from kivy.properties import NumericProperty, StringProperty, ListProperty
from kivy.graphics.texture import Texture
import cv2
import requests
import time
import base64
import json


class HuntGameScreen(Screen):
    score = NumericProperty(0)
    detected_image_name = StringProperty("")
    user_feedback = StringProperty("")
    detected_text = StringProperty("Press START to begin detection")
    feedback_color = ListProperty([0, 1, 0, 1])
    recent_items = set()  # Track recently detected items

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capture = None
        self.current_camera_index = 0
        self.tracker = None
        self.tracking = False
        self.selected_label = ""
        self.awaiting_choice = False
        self.feedback_time = 0

        # Roboflow API configuration
        self.roboflow_api_key = "EOTI0reGUeEwnGjkUTE7"  # From your screenshot
        self.model_name = "trash-detection-2-4oj4h"
        self.model_version = "3"

        # Complete class mapping with recycling information
        self.class_map = {
            # Recyclable items
            "aluminium foil": "recyclable",
            "clear plastic bottle": "recyclable",
            "corrugated carton": "recyclable",
            "drink can": "recyclable",
            "drink carton": "recyclable",
            "food can": "recyclable",
            "glass": "recyclable",
            "glass bottle": "recyclable",
            "glass jar": "recyclable",
            "magazine paper": "recyclable",
            "meal carton": "recyclable",
            "metal": "recyclable",
            "metal bottle cap": "recyclable",
            "metal lid": "recyclable",
            "normal paper": "recyclable",
            "other carton": "recyclable",
            "paper": "recyclable",
            "paper bag": "recyclable",
            "paper cup": "recyclable",
            "plastic bottle cap": "recyclable",
            "plastic lid": "recyclable",
            "pop tab": "recyclable",
            "scrap metal": "recyclable",
            "toilet tube": "recyclable",
            "wrapping paper": "recyclable",

            # Non-recyclable items
            "aerosol": "non-recyclable",
            "aluminium blister pack": "non-recyclable",
            "battery": "non-recyclable",
            "broken glass": "non-recyclable",
            "cigarette": "non-recyclable",
            "crisp packet": "non-recyclable",
            "disposable food container": "non-recyclable",
            "disposable plastic cup": "non-recyclable",
            "egg carton": "non-recyclable",
            "foam cup": "non-recyclable",
            "foam food container": "non-recyclable",
            "food waste": "non-recyclable",
            "garbage bag": "non-recyclable",
            "glass cup": "non-recyclable",
            "other plastic": "non-recyclable",
            "other plastic bottle": "non-recyclable",
            "other plastic wrapper": "non-recyclable",
            "paper straw": "non-recyclable",
            "plastic": "non-recyclable",
            "plastic film": "non-recyclable",
            "plastic glooves": "non-recyclable",
            "plastic straw": "non-recyclable",
            "plastic utensils": "non-recyclable",
            "rope - strings": "non-recyclable",
            "shoe": "non-recyclable",
            "single-use carrier bag": "non-recyclable",
            "six pack rings": "non-recyclable",
            "spread tub": "non-recyclable",
            "squeezable tube": "non-recyclable",
            "styrofoam piece": "non-recyclable",
            "tissues": "non-recyclable",
            "tupperware": "non-recyclable",
            "unlabeled litter": "non-recyclable",
            "waste": "non-recyclable",
        }

    def start_camera(self):
        if not self.capture or not self.capture.isOpened():
            self.capture = cv2.VideoCapture(self.current_camera_index)
            if not self.capture.isOpened():
                self.detected_text = "Error: Unable to access camera"
                return
            Clock.schedule_interval(self.update_frame, 1.0 / 30.0)
            self.detected_text = "Detecting..."
            self.ids.feedback_label.color = [0, 1, 0, 1]

    def stop_camera(self):
        if self.capture and self.capture.isOpened():
            self.capture.release()
        Clock.unschedule(self.update_frame)
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
                self.detected_text = f"Tracking: {self.selected_label}"
            else:
                self.reset_tracking()

        # Detect new objects
        if not self.tracking and not self.awaiting_choice and (current_time - self.feedback_time > 2):
            results = self.detect_with_roboflow(frame)

            if results and 'predictions' in results:
                for pred in results['predictions']:
                    label = pred['class'].lower()

                    if label not in self.class_map:
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

        def find_active_checkbox(widget):
            if isinstance(widget, CheckBox) and widget.active:
                return widget.category
            for child in widget.children:
                result = find_active_checkbox(child)
                if result:
                    return result
            return None

        selected = find_active_checkbox(self.ids.classification_container)

        if selected and self.awaiting_choice:
            detected_obj = self.selected_label.lower()

            # Restrict spamming the same item
            if detected_obj in self.recent_items:
                self.user_feedback = "Item already processed!"
                self.feedback_color = [1, 0.5, 0, 1]  # Orange color for warning
                Clock.schedule_once(lambda dt: setattr(self, 'user_feedback', ""), 2)
                return

            # Add the item to the recent_items set
            self.recent_items.add(detected_obj)

            correct_category = self.class_map.get(detected_obj, "")
            selected_category = selected.lower()

            if selected_category == correct_category:
                self.user_feedback = "Correct! +50 points"
                self.score += 50
                self.feedback_color = [0, 1, 0, 1]
            else:
                self.user_feedback = f"Wrong! {detected_obj} is {correct_category}"
                self.feedback_color = [1, 0, 0, 1]

            self.feedback_time = time.time()
            self.reset_tracking()

            Clock.schedule_once(lambda dt: setattr(self, 'user_feedback', ""), 2)
            Clock.schedule_once(lambda dt: setattr(self, 'feedback_color', [0, 1, 0, 1]), 2)

    def reset_tracking(self):
        self.tracking = False
        self.awaiting_choice = False
        self.selected_label = ""
        self.detected_image_name = ""
        self.detected_text = "Press START to begin detection"
        if self.tracker:
            self.tracker = None

    def clear_recent_items(self):
        self.recent_items.clear()

    def on_leave(self):
        self.stop_camera()