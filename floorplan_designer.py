# floorplan_designer.py
import json
import math
import cv2
import numpy as np
from kivy.metrics import dp
from kivy.app import App  # For popup functionality
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout


class FloorPlanDesignerLogic:
    def __init__(self):
        self.elements = []
        self.history = []
        self.redo_stack = []
        self.grid_size = 20
        self.placing_type = None
        self.rotation = 0
        self.selected_element = None
        self.placing_wall = False
        self.wall_start_point = None
        self.meters_to_pixels_factor = 40
        self.save_history()

    def meters_to_pixels(self, meters):
        """Converts meters to pixels using the defined factor."""
        return meters * self.meters_to_pixels_factor

    def pixels_to_meters(self, pixels):
        """Converts pixels to meters using the defined factor."""
        if self.meters_to_pixels_factor == 0:
            return 0  # Avoid division by zero
        return pixels / self.meters_to_pixels_factor

    def meters_to_pixels_func(self, meters):
        """Alias for meters_to_pixels, matching the Tkinter fix."""
        return self.meters_to_pixels(meters)

    # -------------------------------------

    def set_placing_type(self, ptype):
        """Sets the type of element to be placed next."""
        self.placing_type = ptype
        self.placing_wall = False
        self.selected_element = None

    def start_wall_placement(self):
        """Initiates the wall placement mode."""
        self.placing_wall = True
        self.wall_start_point = None
        self.placing_type = None
        self.selected_element = None

    def add_room(self, x, y, width, height):
        """Adds a room element to the design."""
        self.elements.append({
            "type": "room",
            "x": x,
            "y": y,
            "width": width,
            "height": height
        })
        self.save_history()

    def add_house_border(self, x, y, width, height):
        """Adds a house border element to the design."""
        self.elements.append({
            "type": "houseBorder",
            "x": x,
            "y": y,
            "width": width,
            "height": height
        })
        self.save_history()

    def toggle_rotation(self):
        """Toggles the rotation of the selected element or sets global rotation."""
        if self.selected_element:
            # Toggle rotation for the selected element
            current_rotation = self.selected_element.get("rotation", 0)
            new_rotation = (current_rotation + 90) % 360
            self.selected_element["rotation"] = new_rotation
            self.save_history()
            # Status updates would be handled by the UI layer
        else:
            # If no element is selected, toggle the global rotation for placing new elements
            self.rotation = (self.rotation + 90) % 360
            # Status updates would be handled by the UI layer

    def delete_selected(self):
        """Deletes the currently selected element."""
        if self.selected_element:
            self.elements = [e for e in self.elements if e != self.selected_element]
            self.selected_element = None
            self.save_history()
            # Status updates would be handled by the UI layer

    # Add this method to the FloorPlanDesignerLogic class:
    def set_placing_text(self, text_content, font_size, color_rgba):
        """Sets the text to be placed."""
        self.placing_text = {
            "content": text_content,
            "font_size": font_size,
            "color": color_rgba
        }
        self.placing_type = "text"
        self.placing_wall = False
        self.selected_element = None

    def generate_floor_plan(self, house_x, house_y, house_width, house_height):
        """Generates a floor plan layout scaled to the provided house dimensions."""
        # Clear existing elements
        self.elements = []

        # Add house border
        self.elements.append({
            "type": "houseBorder",
            "x": house_x,
            "y": house_y,
            "width": house_width,
            "height": house_height
        })
        # Define margin and minimum room sizes
        margin = dp(10)
        min_room_width = dp(50)
        min_room_height = dp(80)
        # Calculate room dimensions based on house size
        # Divide house into quadrants for room placement
        usable_width = house_width - 2 * margin
        usable_height = house_height - 2 * margin

        room1_width = max(min_room_width, usable_width * 0.4)  # <-- Problem likely here
        room1_height = max(min_room_height, usable_height * 0.4)  # <-- And here
        room1_x = house_x + margin
        room1_y = house_y + margin
        # Top-right room (e.g., kitchen)
        room2_width = max(min_room_width, usable_width * 0.5)  # <-- Problem likely here
        room2_height = max(min_room_height, usable_height * 0.5)  # <-- And here
        room2_x = house_x + house_width - margin - room2_width
        room2_y = house_y + margin
        # Bottom-left room (e.g., living room)
        room3_width = max(min_room_width, usable_width * 0.5)  # <-- Problem likely here
        room3_height = max(min_room_height, usable_height * 0.4)  # <-- And here
        room3_x = house_x + margin
        room3_y = house_y + house_height - margin - room3_height
        # Bottom-right room (e.g., bathroom)
        room4_width = max(min_room_width, usable_width * 0.4)  # <-- Problem likely here
        room4_height = max(min_room_height, usable_height * 0.4)  # <-- And here
        room4_x = house_x + house_width - margin - room4_width
        room4_y = house_y + house_height - margin - room4_height

        # --- Add Rooms ---
        self.elements.append({
            "type": "room",  # Standard room (Bedroom)
            "name": "room",
            "x": room1_x,
            "y": room1_y,
            "width": room1_width,
            "height": room1_height
        })

        self.elements.append({
            "type": "room",  # Kitchen
            "name": "kitchen",
            "x": room2_x,
            "y": room2_y,
            "width": room2_width,
            "height": room2_height
        })

        self.elements.append({
            "type": "room",  # Living Room
            "name": "living_room",
            "x": room3_x,
            "y": room3_y,
            "width": room3_width,
            "height": room3_height
        })

        self.elements.append({
            "type": "room",  # Bathroom
            "name": "bathroom",
            "x": room4_x,
            "y": room4_y,
            "width": room4_width,
            "height": room4_height
        })

        # --- Add Appliances using the helper function logic ---
        # Appliances are positioned relative to their room's top-left corner

        # Bedroom appliances (Top-left room)
        self.add_appliances_to_room_scaled("room", room1_x, room1_y, room1_width, room1_height)

        # Kitchen appliances (Top-right room)
        self.add_appliances_to_room_scaled("kitchen", room2_x, room2_y, room2_width, room2_height)

        # Living room appliances (Bottom-left room)
        self.add_appliances_to_room_scaled("living_room", room3_x, room3_y, room3_width, room3_height)

        # Bathroom appliances (Bottom-right room)
        self.add_appliances_to_room_scaled("bathroom", room4_x, room4_y, room4_width, room4_height)

        # Add outer doors and windows
        self.elements.append({
            "type": "door",
            "x": house_x,
            "y": house_y + house_height / 2 - dp(20)
        })

        self.elements.append({
            "type": "window",
            "x": house_x + house_width / 4,
            "y": house_y + dp(6)
        })

        # Validate that appliances fit in their rooms
        self.validate_appliances_in_rooms()
        self.save_history()

    def add_appliances_to_room_scaled(self, room_type, room_x, room_y, room_width, room_height):
        base_sizes = {
            "room": {"width": dp(100), "height": dp(150)},
            "kitchen": {"width": dp(250), "height": dp(200)},
            "living_room": {"width": dp(200), "height": dp(150)},
            "bathroom": {"width": dp(200), "height": dp(200)}
        }

        base_size = base_sizes.get(room_type, {"width": dp(100), "height": dp(150)})
        base_width = base_size["width"]
        base_height = base_size["height"]

        try:
            scale_x = room_width / base_width
        except ZeroDivisionError:
            scale_x = 1.0
        try:
            scale_y = room_height / base_height
        except ZeroDivisionError:
            scale_y = 1.0

        if room_type == "room":
            self.elements.append({
                "type": "bed-queen",
                "x": room_x + dp(20) * scale_x,
                "y": room_y + dp(20) * scale_y
            })
            self.elements.append({
                "type": "side-table",
                "x": room_x + dp(68) * scale_x,
                "y": room_y + dp(20) * scale_y
            })
            # Door position adjusted to stay near the right wall
            self.elements.append({
                "type": "door",
                "x": room_x + room_width - dp(1),  # Fixed inset from right edge
                "y": room_y + dp(70) * scale_y,
                "rotation": 180  # Facing left
            })

        elif room_type == "kitchen":
            self.elements.append({
                "type": "sink",
                "x": room_x + dp(20) * scale_x,
                "y": room_y + dp(20) * scale_y
            })

            self.elements.append({
                "type": "window",
                "x": room_x + room_width - dp(200),  # Center horizontally in the room
                "y": room_y + room_height - dp(204) * scale_y,  # Near the top wall
                "width": dp(40) * scale_x,
                "height": dp(20) * scale_y
            })

            self.elements.append({
                "type": "gas-stove",
                "x": room_x + dp(80) * scale_x,
                "y": room_y + dp(20) * scale_y
            })
            self.elements.append({
                "type": "fridge",
                "x": room_x + room_width - dp(50) * scale_x,  # Scaled to stay near right wall
                "y": room_y + dp(10) * scale_y
            })
            self.elements.append({
                "type": "table",
                "x": room_x + dp(50) * scale_x,
                "y": room_y + dp(100) * scale_y
            })
            # Door position adjusted to stay near the bottom wall
            self.elements.append({
                "type": "door",
                "x": room_x + dp(200) * scale_x,
                "y": room_y + room_height - dp(15) * scale_y,  # Scaled inset from bottom edge
                "rotation": 270  # Facing down
            })

        elif room_type == "living_room":
            self.elements.append({
                "type": "sofa",
                "x": room_x + dp(10) * scale_x,
                "y": room_y + dp(60) * scale_y,
                "rotation": 270
            })

            self.elements.append({
                "type": "window",
                "x": room_x + room_width - dp(320),  # Center horizontally in the room
                "y": room_y + room_height - dp(70) * scale_y,  # Near the top wall
                "width": dp(40) * scale_x,
                "height": dp(20) * scale_y,
                "rotation": 90
            })

            self.elements.append({
                "type": "sofa",
                "x": room_x + dp(100) * scale_x,
                "y": room_y + dp(20) * scale_y
            })
            # TV position - properly scaled to stay near bottom wall
            self.elements.append({
                "type": "flat-tv",
                "x": room_x + dp(100) * scale_x,
                "y": room_y + room_height - dp(40) * scale_y  # Scaled inset from bottom edge
            })
            # Door position - properly scaled to stay near right wall
            self.elements.append({
                "type": "door",
                "x": room_x + room_width - dp(1) * scale_x,  # Scaled inset from right edge
                "y": room_y + dp(100) * scale_y,
                "rotation": 180  # Facing left
            })
        elif room_type == "bathroom":
            self.elements.append({
                "type": "toilet",
                "x": room_x + dp(20) * scale_x,
                "y": room_y + dp(20) * scale_y,
                "rotation": 270
            })
            self.elements.append({
                "type": "bathtub",
                "x": room_x + dp(100) * scale_x,
                "y": room_y + dp(120) * scale_y
            })
            self.elements.append({
                "type": "shower",
                "x": room_x + dp(20) * scale_x,
                "y": room_y + dp(120) * scale_y
            })
            # Door position adjusted to stay near the bottom wall
            self.elements.append({
                "type": "door",
                "x": room_x + dp(120) * scale_x,
                "y": room_y + room_height - dp(230) * scale_y,  # Scaled inset from bottom edge
                "rotation": 90  # Facing down
            })

    def validate_appliances_in_rooms(self):
        """Check if appliances fit within their rooms and show popup if not."""
        # Check living room appliances
        living_room = None
        for element in self.elements:
            if element["type"] == "room" and element["x"] == dp(50) and element["y"] == dp(50):
                living_room = element
                break
        if living_room:
            # Check if sofa fits in living room
            sofa = None
            for element in self.elements:
                if element["type"] == "sofa":
                    sofa = element
                    break
            if sofa:
                # Get sofa size
                sofa_size = self.get_appliance_size("sofa")
                sofa_width = sofa_size["width"]
                sofa_height = sofa_size["height"]
                # Check if sofa fits in living room
                if (sofa["x"] + sofa_width > living_room["x"] + living_room["width"] or
                        sofa["y"] + sofa_height > living_room["y"] + living_room["height"]):
                    self.show_room_too_small_popup("living room")
        # Check kitchen appliances
        kitchen_room = None
        for element in self.elements:
            if element["type"] == "room" and element["x"] == dp(350) and element["y"] == dp(50):
                kitchen_room = element
                break
        if kitchen_room:
            # Check if sink fits in kitchen room
            sink = None
            for element in self.elements:
                if element["type"] == "sink":
                    sink = element
                    break
            if sink:
                # Get sink size
                sink_size = self.get_appliance_size("sink")
                sink_width = sink_size["width"]
                sink_height = sink_size["height"]
                # Check if sink fits in kitchen room
                if (sink["x"] + sink_width > kitchen_room["x"] + kitchen_room["width"] or
                        sink["y"] + sink_height > kitchen_room["y"] + kitchen_room["height"]):
                    self.show_room_too_small_popup("kitchen")
        # Check bathroom appliances
        bathroom_room = None
        for element in self.elements:
            if element["type"] == "room" and element["x"] == dp(500) and element["y"] == dp(50):
                bathroom_room = element
                break
        if bathroom_room:
            # Check if toilet fits in bathroom room
            toilet = None
            for element in self.elements:
                if element["type"] == "toilet":
                    toilet = element
                    break
            if toilet:
                # Get toilet size
                toilet_size = self.get_appliance_size("toilet")
                toilet_width = toilet_size["width"]
                toilet_height = toilet_size["height"]
                # Check if toilet fits in bathroom room
                if (toilet["x"] + toilet_width > bathroom_room["x"] + bathroom_room["width"] or
                        toilet["y"] + toilet_height > bathroom_room["y"] + bathroom_room["height"]):
                    self.show_room_too_small_popup("bathroom")
        # Check bedroom appliances
        bedroom_room = None
        for element in self.elements:
            if element["type"] == "room" and element["x"] == dp(50) and element["y"] == dp(250):
                bedroom_room = element
                break
        if bedroom_room:
            # Check if bed fits in bedroom room
            bed = None
            for element in self.elements:
                if element["type"] == "bed-queen":
                    bed = element
                    break
            if bed:
                # Get bed size
                bed_size = self.get_appliance_size("bed-queen")
                bed_width = bed_size["width"]
                bed_height = bed_size["height"]
                # Check if bed fits in bedroom room
                if (bed["x"] + bed_width > bedroom_room["x"] + bedroom_room["width"] or
                        bed["y"] + bed_height > bedroom_room["y"] + bedroom_room["height"]):
                    self.show_room_too_small_popup("bedroom")

    def show_room_too_small_popup(self, room_name="House"):
        # Create popup content
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        # Create label with message
        message_label = Label(
            text=f"The {room_name} is too small! Please adjust the room size.\nWidth must be at least 15m and Height at least 10.75m.",
            size_hint_y=None,
            # Adjust height and text_size for the longer message
            height=dp(70),
            text_size=(dp(300), None)  # Allow text wrapping
        )
        layout.add_widget(message_label)

        # Create close button
        close_button = Button(text="Close", size_hint_y=None, height=dp(40))
        layout.add_widget(close_button)

        # Create popup
        popup = Popup(
            title="Room Size Error",
            content=layout,
            size_hint=(None, None),
            # Adjust popup size if needed
            size=(dp(350), dp(220))
        )

        # Bind close button to dismiss popup
        close_button.bind(on_press=popup.dismiss)

        # Open popup
        popup.open()

        layout.add_widget(message_label)
        # Create OK button
        ok_button = Button(text='OK', size_hint_y=None, height=dp(40))
        ok_button.bind(on_press=lambda x: popup.dismiss())
        layout.add_widget(ok_button)
        # Create popup
        popup = Popup(
            title='Room Too Small',
            content=layout,
            size_hint=(0.8, 0.6)
        )
        # Show popup
        popup.open()

    def add_preset(self, preset_type):
        """Adds a predefined set of elements."""
        offset_x, offset_y = dp(50), dp(50)  # Example offset using dp
        if preset_type == "room":
            self.elements.append({"type": "room", "x": offset_x, "y": offset_y, "width": dp(200), "height": dp(150)})
            self.elements.append({"type": "bed-queen", "x": offset_x + dp(20), "y": offset_y + dp(20)})
            self.elements.append({"type": "side-table", "x": offset_x + dp(130), "y": offset_y + dp(20)})
            self.elements.append({"type": "door", "x": offset_x + dp(200), "y": offset_y + dp(70), "rotation": 180})
        elif preset_type == "kitchen":
            self.elements.append(
                {"type": "room", "x": offset_x + dp(300), "y": offset_y, "width": dp(250), "height": dp(200)})
            self.elements.append({"type": "sink", "x": offset_x + dp(320), "y": offset_y + dp(20)})
            self.elements.append({"type": "gas-stove", "x": offset_x + dp(380), "y": offset_y + dp(20)})
            self.elements.append({"type": "fridge", "x": offset_x + dp(500), "y": offset_y + dp(10)})
            self.elements.append({"type": "table", "x": offset_x + dp(350), "y": offset_y + dp(100)})
            self.elements.append(
                {"type": "door", "x": offset_x + dp(500), "y": offset_y + dp(187), "rotation": 270})  # Door at bottom
        elif preset_type == "livingroom":
            self.elements.append(
                {"type": "room", "x": offset_x, "y": offset_y + dp(250), "width": dp(250), "height": dp(200)})
            self.elements.append({"type": "sofa", "x": offset_x + dp(10), "y": offset_y + dp(310), "rotation": 270})
            self.elements.append(
                {"type": "sofa", "x": offset_x + dp(110), "y": offset_y + dp(270)})  # Facing
            self.elements.append(
                {"type": "side-table", "x": offset_x + dp(140), "y": offset_y + dp(340)})  # Might overlap
            self.elements.append({"type": "flat-tv", "x": offset_x + dp(120), "y": offset_y + dp(410)})
            self.elements.append({"type": "door", "x": offset_x + dp(250), "y": offset_y + dp(340), "rotation": 180})
        elif preset_type == "bathroom":
            self.elements.append(
                {"type": "room", "x": offset_x + dp(350), "y": offset_y + dp(250), "width": dp(200), "height": dp(200)})
            self.elements.append({"type": "toilet", "x": offset_x + dp(370), "y": offset_y + dp(270), "rotation": 270})
            self.elements.append({"type": "bathtub", "x": offset_x + dp(440), "y": offset_y + dp(390)})
            self.elements.append({"type": "shower", "x": offset_x + dp(370), "y": offset_y + dp(380)})
            self.elements.append({"type": "door", "x": offset_x + dp(470), "y": offset_y + dp(225), "rotation": 90})
        self.save_history()

    # --- Image Scanning Logic (adapted from Tkinter) ---
    def scan_image(self, image_path):
        try:
            # ---- OpenCV Image Processing Pipeline ----
            # 1. Load Image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError("Could not load image. Check file format.")
            orig_height, orig_width = img.shape[:2]
            # 2. Resize for processing
            max_dim = 1200
            if max(orig_width, orig_height) > max_dim:
                scale = max_dim / max(orig_width, orig_height)
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)
                img_resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            else:
                img_resized = img
                scale = 1.0
            # 3. Convert to Grayscale
            gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
            # 4. Preprocessing
            blurred = cv2.GaussianBlur(gray, (7, 7), 0)
            # 5. Edge Detection
            edges = cv2.Canny(blurred, threshold1=30, threshold2=90, apertureSize=3)
            # 6. Morphological Operations
            kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
            kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
            edges_closed_h = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_h)
            edges_closed_v = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_v)
            edges_combined = cv2.bitwise_or(edges_closed_h, edges_closed_v)
            kernel_general = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            edges_final = cv2.morphologyEx(edges_combined, cv2.MORPH_CLOSE, kernel_general)
            # ---- Line Detection ----
            # self.update_status("Scanning image (detecting lines)...") # Handled by UI
            lines = cv2.HoughLinesP(edges_final, rho=1, theta=np.pi / 180, threshold=80, minLineLength=50,
                                    maxLineGap=20)
            scanned_elements = []
            walls_found = 0
            if lines is not None:
                horizontal_lines = []
                vertical_lines = []
                other_lines = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                    angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                    if angle < 10 or angle > 170:
                        horizontal_lines.append((x1, y1, x2, y2, length))
                    elif 80 < angle < 100:
                        vertical_lines.append((x1, y1, x2, y2, length))
                    else:
                        other_lines.append((x1, y1, x2, y2, length))
                if horizontal_lines and vertical_lines:
                    horizontal_lines.sort(key=lambda l: l[4], reverse=True)
                    vertical_lines.sort(key=lambda l: l[4], reverse=True)
                    border_h_lines = horizontal_lines[:2]
                    border_v_lines = vertical_lines[:2]
                    for x1, y1, x2, y2, _ in border_h_lines:
                        scanned_elements.append({
                            "type": "wall",
                            "x1": float(x1 / scale),
                            "y1": float(y1 / scale),
                            "x2": float(x2 / scale),
                            "y2": float(y2 / scale)
                        })
                        walls_found += 1
                    for x1, y1, x2, y2, _ in border_v_lines:
                        scanned_elements.append({
                            "type": "wall",
                            "x1": float(x1 / scale),
                            "y1": float(y1 / scale),
                            "x2": float(x2 / scale),
                            "y2": float(y2 / scale)
                        })
                        walls_found += 1
                all_other_lines = other_lines + horizontal_lines[2:] + vertical_lines[2:]
                all_other_lines.sort(key=lambda l: l[4], reverse=True)
                lines_to_add = min(30, len(all_other_lines))
                for i in range(lines_to_add):
                    x1, y1, x2, y2, length = all_other_lines[i]
                    if length > 30:
                        scanned_elements.append({
                            "type": "wall",
                            "x1": float(x1 / scale),
                            "y1": float(y1 / scale),
                            "x2": float(x2 / scale),
                            "y2": float(y2 / scale)
                        })
                        walls_found += 1
            rooms_found = 0
            _, thresh_for_rooms = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            kernel_room = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            thresh_morphed = cv2.morphologyEx(thresh_for_rooms, cv2.MORPH_CLOSE, kernel_room)
            contours, _ = cv2.findContours(thresh_morphed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 5000 / (scale * scale):
                    epsilon = 0.03 * cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, epsilon, True)
                    if len(approx) == 4:
                        x_rect, y_rect, w_rect, h_rect = cv2.boundingRect(cnt)
                        aspect_ratio = float(w_rect) / h_rect if h_rect > 0 else float('inf')
                        if 0.3 < aspect_ratio < 3.5 and w_rect > 30 / scale and h_rect > 30 / scale:
                            scanned_elements.append({
                                "type": "room",
                                "x": float(x_rect / scale),
                                "y": float(y_rect / scale),
                                "width": float(w_rect / scale),
                                "height": float(h_rect / scale)
                            })
                            rooms_found += 1
            circles_found = 0
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=20,
                param1=50,
                param2=25,
                minRadius=5,
                maxRadius=30
            )
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                for (x, y, r) in circles:
                    scanned_elements.append({
                        "type": "toilet",  # Assume
                        "x": float((x - r) / scale),
                        "y": float((y - r) / scale),
                        "width": float(2 * r / scale),
                        "height": float(2 * r / scale)
                    })
                    circles_found += 1

            return True, scanned_elements, rooms_found, walls_found, circles_found  # Return status and elements for UI
        except Exception as e:
            print(f"Scan error in logic: {e}")  # Log or handle in UI
            return False, [], 0, 0, 0  # Return failure status

    # ------------------------------------

    def save_history(self):
        """Saves the current state to the history stack."""
        self.history.append(json.dumps(self.elements))
        self.redo_stack = []

    def undo(self):
        """Undoes the last action."""
        if len(self.history) > 1:
            self.redo_stack.append(self.history.pop())
            self.elements = json.loads(self.history[-1])
            self.selected_element = None

    def redo(self):
        """Redoes the previously undone action."""
        if self.redo_stack:
            self.history.append(self.redo_stack.pop())
            self.elements = json.loads(self.history[-1])
            self.selected_element = None

    def get_appliance_size(self, appliance_type):
        sizes = {
            "bed-single": {"width": dp(60), "height": dp(100)},
            "bed-double": {"width": dp(80), "height": dp(100)},
            "bed-queen": {"width": dp(100), "height": dp(100)},
            "bed-king": {"width": dp(120), "height": dp(100)},
            "table": {"width": dp(120), "height": dp(80)},
            "sofa": {"width": dp(100), "height": dp(50)},
            "fridge": {"width": dp(45), "height": dp(70)},
            "sink": {"width": dp(50), "height": dp(35)},
            "toilet": {"width": dp(35), "height": dp(50)},
            "door": {"width": dp(8), "height": dp(40)},  # Width is usually small
            "double-door": {"width": dp(16), "height": dp(40)},  # Double the width of a single door
            "window": {"width": dp(60), "height": dp(8)},
            "shower": {"width": dp(40), "height": dp(60)},
            "flat-tv": {"width": dp(70), "height": dp(15)},
            "gas-stove": {"width": dp(45), "height": dp(30)},
            "side-table": {"width": dp(35), "height": dp(35)},
            "bathtub": {"width": dp(90), "height": dp(45)},
            "chair": {"width": dp(20), "height": dp(20)}  # Small square
        }
        default_size = {"width": dp(40), "height": dp(40)}
        return sizes.get(appliance_type, default_size)

    # Add methods for save/load layout (JSON handling) as needed
    def save_layout_to_json(self):
        layout_data = {
            "version": "1.0",
            "created": str(__import__('datetime').datetime.now()),
            "grid_size": self.grid_size,
            "meters_to_pixels_factor": self.meters_to_pixels_factor,
            "elements": self.elements
        }
        return json.dumps(layout_data, indent=2)

    def load_layout_from_json(self, json_string):

        try:
            data = json.loads(json_string)
            # Handle both old format (just elements) and new format (with metadata)
            if "elements" in data:
                self.elements = data["elements"]
                # Restore metadata if available
                if "grid_size" in data:
                    self.grid_size = data["grid_size"]
                if "meters_to_pixels_factor" in data:
                    self.meters_to_pixels_factor = data["meters_to_pixels_factor"]
            else:
                # Assume it's just the elements array
                self.elements = data
            self.selected_element = None
            self.save_history()
            return True
        except Exception as e:
            print(f"Error loading layout: {e}")
            return False

    def set_placing_type(self, element_type):
        self.placing_type = element_type
        self.selected_element = None
        self.placing_wall = False