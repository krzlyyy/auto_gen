# widgets.py
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Rectangle, Ellipse, InstructionGroup, PushMatrix, PopMatrix, Rotate
from kivy.graphics.transformation import Matrix
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.metrics import dp
import math

class FloorPlanCanvas(Widget):
    def __init__(self, designer_logic, **kwargs):
        super().__init__(**kwargs)
        self.designer_logic = designer_logic
        self.grid_size = self.designer_logic.grid_size
        self.bind(size=self.redraw, pos=self.redraw) # Redraw on resize/pos change

        # --- Add White Background ---
        self.bg_layer = InstructionGroup()
        with self.canvas.before:
            Color(1, 1, 1, 1) # White color (R, G, B, A)

            self.bg_rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(size=self._update_bg_rect, pos=self._update_bg_rect)

        self.canvas.add(self.bg_layer)
        # --------------------------

        # Touch interaction state
        self.touch_start_pos = (0, 0)
        self.dragging_element = None
        self.resizing_corner = None
        self.element_start_x = 0
        self.element_start_y = 0
        self.element_start_width = 0
        self.element_start_height = 0

        # Instruction Groups for layers
        self.grid_layer = InstructionGroup()
        self.elements_layer = InstructionGroup()
        self.selection_layer = InstructionGroup()
        self.preview_layer = InstructionGroup() # For wall placement preview
        self.canvas.add(self.grid_layer)
        self.canvas.add(self.elements_layer)
        self.canvas.add(self.selection_layer)
        self.canvas.add(self.preview_layer)

        # --- Add dictionary to track text labels ---
        self.text_labels = {} # Maps element id to Label widget

        self.redraw()

    def _update_bg_rect(self, instance, value):

        if hasattr(self, 'bg_rect'): # Safety check
            self.bg_rect.size = instance.size
            self.bg_rect.pos = instance.pos

    def redraw(self, *args):
        self.draw_grid()
        self.draw_elements()
        self.draw_selection() # Draw selection/highlights

    def draw_grid(self):
        self.grid_layer.clear()
        if self.grid_size <= 0:
            return


        width, height = self.size
        x_offset, y_offset = self.pos

        # Add drawing instructions directly to the grid_layer InstructionGroup
        self.grid_layer.add(Color(0.87, 0.87, 0.87, 1)) # #ddd

        # Draw lines within the widget's area
        # Vertical lines
        for x in range(0, int(width) + self.grid_size, self.grid_size):
            line_instruction = Line(points=[x_offset + x, y_offset, x_offset + x, y_offset + height], width=1)
            self.grid_layer.add(line_instruction)

        # Horizontal lines
        for y in range(0, int(height) + self.grid_size, self.grid_size):
            line_instruction = Line(points=[x_offset, y_offset + y, x_offset + width, y_offset + y], width=1)
            self.grid_layer.add(line_instruction)

    def draw_elements(self):
        self.elements_layer.clear()

        current_element_ids = {id(element) for element in self.designer_logic.elements}
        labels_to_remove = []
        for element_id, label in self.text_labels.items():
            if element_id not in current_element_ids:
                labels_to_remove.append(element_id)
                if label.parent is self: # Check if it's actually a child
                    self.remove_widget(label) # Remove the Label widget
        for element_id in labels_to_remove:
            del self.text_labels[element_id]

        for element in self.designer_logic.elements:
            self.draw_element(element)

    def draw_element(self, element):

        element_type = element.get("type")
        x, y = element.get("x", 0), element.get("y", 0)

        rotation = element.get("rotation", 0)
        should_rotate = rotation != 0 and element_type not in ["wall"] # Walls don't rotate
        if should_rotate:

            if element_type in ["room", "houseBorder"]:
                w, h = element["width"], element["height"]
            else:
                size = self.designer_logic.get_appliance_size(element_type)
                w, h = size["width"], size["height"]

            # Apply rotation transformation
            self.elements_layer.add(PushMatrix())
            # Rotate around the center of the element
            pivot_x = x + w / 2.0
            pivot_y = y + h / 2.0
            self.elements_layer.add(Rotate(angle=rotation, origin=(pivot_x, pivot_y)))

        # Draw the specific element type
        if element_type == "room":
            self._draw_single_line_rect(element["x"], element["y"], element["width"], element["height"])
        elif element_type == "houseBorder":
            self._draw_house_border(element["x"], element["y"], element["width"], element["height"])
        elif element_type == "wall":
            self._draw_wall(element["x1"], element["y1"], element["x2"], element["y2"])
        else: # Appliances (including text)
            self._draw_appliance(element)

        if should_rotate:
            self.elements_layer.add(PopMatrix()) # Revert transformation

    def _draw_single_line_rect(self, x, y, width, height):
        self.elements_layer.add(Color(0, 0, 0, 1)) # Black
        line_instruction = Line(rectangle=(x, y, width, height), width=2)
        self.elements_layer.add(line_instruction)

    def _draw_house_border(self, x, y, width, height):
         border_width = dp(10)
         self.elements_layer.add(Color(0, 0, 0, 1)) # Black
         # Outer border
         self.elements_layer.add(Line(rectangle=(x, y, width, height), width=2))
         # Inner border
         self.elements_layer.add(Line(rectangle=(x + border_width, y + border_width, width - 2 * border_width, height - 2 * border_width), width=2))
         # Window line (simplified)
         self.elements_layer.add(Line(points=[x + width / 2 - dp(15), y + border_width / 2, x + width / 2 + dp(15), y + border_width / 2], width=4))
         # Door opening (white rectangle to erase part of wall)
         self.elements_layer.add(Color(1, 1, 1, 1)) # White
         self.elements_layer.add(Rectangle(pos=(x, y + height / 2 - dp(20)), size=(border_width, dp(40))))
         self.elements_layer.add(Color(0, 0, 0, 1)) # Black
         # Door frame
         self.elements_layer.add(Line(rectangle=(x - dp(2), y + height / 2 - dp(20), border_width + dp(4), dp(40)), width=3))

    def _draw_wall(self, x1, y1, x2, y2):
        self.elements_layer.add(Color(0, 0, 0, 1)) # Black
        line_instruction = Line(points=[x1, y1, x2, y2], width=2)
        self.elements_layer.add(line_instruction)

    def _draw_appliance(self, element):
        x, y = element["x"], element["y"]
        etype = element["type"]

        size = element.get("customSize", self.designer_logic.get_appliance_size(etype))
        width, height = size["width"], size["height"]

        self.elements_layer.add(Color(0, 0, 0, 1))  # Default black outline

        if etype == "text":

            content = element.get("content", "Text")


            font_size_sp = element.get("fontSize", 14)


            text_color = [0, 0, 0, 1] # Black RGBA


            element_key = id(element)
            label = None


            if element_key in self.text_labels:
                label = self.text_labels[element_key]

                label.text = content
                label.pos = (x, y)
                label.size = (width, height)

                label.font_size = f"{font_size_sp}sp"

                label.color = text_color
            else:
                # Create a new Label widget with properties from element
                label = Label(
                    text=content,
                    pos=(x, y),
                    size=(width, height),

                    font_size=f"{font_size_sp}sp",  # Set initial font size
                    color=text_color  # Set initial text color to black
                )
                # Add the label as a child widget of the canvas widget
                self.add_widget(label)
                # Store the reference
                self.text_labels[element_key] = label

            return


        if etype in ["bed-single", "bed-double", "bed-queen", "bed-king"]:
            # White mattress
            self.elements_layer.add(Color(1, 1, 1, 1)) # White fill
            self.elements_layer.add(Rectangle(pos=(x, y), size=(width, height)))
            self.elements_layer.add(Color(0, 0, 0, 1)) # Black outline
            self.elements_layer.add(Line(rectangle=(x, y, width, height), width=2))

            # Gray pillows (top)
            pillow_h = dp(15)
            self.elements_layer.add(Color(0.94, 0.94, 0.94, 1)) # #f0f0f0
            self.elements_layer.add(Rectangle(pos=(x + dp(5), y + dp(5)), size=(width - dp(10), pillow_h)))
            self.elements_layer.add(Color(0, 0, 0, 1))
            self.elements_layer.add(Line(rectangle=(x + dp(5), y + dp(5), width - dp(10), pillow_h), width=1))

            # Light gray blanket
            blanket_y = y + dp(5) + pillow_h + dp(5)
            self.elements_layer.add(Color(0.88, 0.88, 0.88, 1)) # #e0e0e0
            self.elements_layer.add(Rectangle(pos=(x + dp(5), blanket_y), size=(width - dp(10), height - dp(5) - (blanket_y - y))))
            self.elements_layer.add(Color(0, 0, 0, 1))
            self.elements_layer.add(Line(rectangle=(x + dp(5), blanket_y, width - dp(10), height - dp(5) - (blanket_y - y)), width=1))

        elif etype == "table":
            # Table top
            self.elements_layer.add(Line(rectangle=(x, y, width, height), width=2))

            # Simplified chairs (small squares instead of lines/slashes)
            chair_size = dp(12)
            self.elements_layer.add(Color(0, 0, 0, 1))

            # Top chairs
            self.elements_layer.add(
                Rectangle(pos=(x + width / 4 - chair_size / 2, y - chair_size - dp(3)), size=(chair_size, chair_size)))
            self.elements_layer.add(Rectangle(pos=(x + 3 * width / 4 - chair_size / 2, y - chair_size - dp(3)),
                                              size=(chair_size, chair_size)))

            # Bottom chairs
            self.elements_layer.add(
                Rectangle(pos=(x + width / 4 - chair_size / 2, y + height + dp(3)), size=(chair_size, chair_size)))
            self.elements_layer.add(
                Rectangle(pos=(x + 3 * width / 4 - chair_size / 2, y + height + dp(3)), size=(chair_size, chair_size)))

            # Side chairs
            self.elements_layer.add(
                Rectangle(pos=(x - chair_size - dp(3), y + height / 2 - chair_size / 2), size=(chair_size, chair_size)))
            self.elements_layer.add(
                Rectangle(pos=(x + width + dp(3), y + height / 2 - chair_size / 2), size=(chair_size, chair_size)))

        elif etype == "sofa":
            body_pad = dp(8)
            # Main body/backrest
            self.elements_layer.add(Color(0.82, 0.82, 0.82, 1)) # #d0d0d0
            self.elements_layer.add(Rectangle(pos=(x, y), size=(width, height)))
            self.elements_layer.add(Rectangle(pos=(x - body_pad, y - dp(5)), size=(width + 2 * body_pad, dp(12))))

            # Armrests
            self.elements_layer.add(Rectangle(pos=(x - body_pad, y), size=(body_pad, height)))
            self.elements_layer.add(Rectangle(pos=(x + width, y), size=(body_pad, height)))

            self.elements_layer.add(Color(0, 0, 0, 1)) # Black outline
            self.elements_layer.add(Line(rectangle=(x, y, width, height), width=2))
            self.elements_layer.add(Line(points=[x - body_pad, y - dp(5), x + width + body_pad, y - dp(5)], width=1))
            self.elements_layer.add(Line(points=[x - body_pad, y + height, x - body_pad, y], width=1))
            self.elements_layer.add(Line(points=[x + width + body_pad, y, x + width + body_pad, y + height], width=1))

        elif etype == "fridge":
            self.elements_layer.add(Color(1, 1, 1, 1)) # White
            self.elements_layer.add(Rectangle(pos=(x, y), size=(width, height)))
            self.elements_layer.add(Color(0, 0, 0, 1)) # Black
            self.elements_layer.add(Line(rectangle=(x, y, width, height), width=2))

            # Door separation line
            self.elements_layer.add(Line(points=[x, y + height / 2, x + width, y + height / 2], width=1))

            # Handles
            handle_offset = dp(8)
            handle_len = dp(6)
            self.elements_layer.add(Line(points=[x + width - handle_offset, y + height / 4 - handle_len/2, x + width - handle_offset, y + height / 4 + handle_len/2], width=2))
            self.elements_layer.add(Line(points=[x + width - handle_offset, y + 3 * height / 4 - handle_len/2, x + width - handle_offset, y + 3 * height / 4 + handle_len/2], width=2))

        elif etype == "sink":
            self.elements_layer.add(Line(rectangle=(x, y, width, height), width=2))

            # Oval basin
            basin_pad = dp(8)
            # Kivy doesn't have direct Oval, approximate with Ellipse
            self.elements_layer.add(Ellipse(pos=(x + basin_pad, y + basin_pad), size=(width - 2 * basin_pad, height - 2 * basin_pad), width=1))

            # Faucet
            faucet_r = dp(4)
            faucet_y = y + dp(8)
            self.elements_layer.add(Ellipse(pos=(x + width / 2 - faucet_r, faucet_y - faucet_r), size=(2 * faucet_r, 2 * faucet_r), width=1))
            self.elements_layer.add(Line(points=[x + width / 2, faucet_y + faucet_r, x + width / 2, faucet_y + faucet_r + dp(6)], width=1))

        elif etype == "toilet":
            tank_h = height * 0.4
            tank_w = width - dp(6)
            self.elements_layer.add(Color(1, 1, 1, 1)) # White
            self.elements_layer.add(Rectangle(pos=(x + dp(3), y), size=(tank_w, tank_h)))
            self.elements_layer.add(Color(0, 0, 0, 1)) # Black
            self.elements_layer.add(Line(rectangle=(x + dp(3), y, tank_w, tank_h), width=2))

            # Bowl
            bowl_pad_x = dp(5)
            bowl_pad_y = dp(8)
            bowl_y = y + tank_h + bowl_pad_y
            bowl_h = height - tank_h - 2 * bowl_pad_y
            self.elements_layer.add(Ellipse(pos=(x + bowl_pad_x, bowl_y), size=(width - 2 * bowl_pad_x, bowl_h), width=2))

            # Flush button
            button_w, button_h = dp(6), dp(4)
            self.elements_layer.add(Color(0.75, 0.75, 0.75, 1)) # Silver #c0c0c0 is close
            self.elements_layer.add(Rectangle(pos=(x + width / 2 - button_w/2, y + dp(8)), size=(button_w, button_h)))
            self.elements_layer.add(Color(0, 0, 0, 1))
            self.elements_layer.add(Line(rectangle=(x + width / 2 - button_w/2, y + dp(8), button_w, button_h), width=1))

        elif etype == "door":
            door_width, door_height = width, height
            # Door jamb
            self.elements_layer.add(Line(points=[x, y, x, y + door_height], width=3))

            # Door panel
            self.elements_layer.add(Line(points=[x, y, x + door_width, y], width=3))

            # Door swing arc (approximated)
            arc_points = []
            arc_radius = door_height
            center_x, center_y = x, y
            for angle_deg in range(0, 91, 15):
                angle_rad = math.radians(angle_deg)
                px = center_x + arc_radius * math.cos(angle_rad)
                py = center_y + arc_radius * math.sin(angle_rad)
                arc_points.extend([px, py])
            if len(arc_points) >= 4:
                self.elements_layer.add(Line(points=arc_points, width=2))

            # Handle
            handle_r = dp(2)
            handle_x = x + door_width - dp(5)
            handle_y = y + door_height / 2
            self.elements_layer.add(Color(0, 0, 0, 1)) # Black
            self.elements_layer.add(Ellipse(pos=(handle_x - handle_r, handle_y - handle_r), size=(2 * handle_r, 2 * handle_r)))

        elif etype == "double-door":
            door_width, door_height = width, height
            # Door jamb
            self.elements_layer.add(Line(points=[x, y, x, y + door_height], width=3))

            # Door panel (left door)
            self.elements_layer.add(Line(points=[x, y, x + door_width/2, y], width=3))

            # Door panel (right door)
            self.elements_layer.add(Line(points=[x + door_width/2, y, x + door_width, y], width=3))

            # Door swing arcs (approximated)
            arc_points_left = []
            arc_points_right = []
            arc_radius = door_height
            center_x_left, center_y_left = x, y
            center_x_right, center_y_right = x + door_width, y
            for angle_deg in range(0, 91, 15):
                angle_rad = math.radians(angle_deg)
                # Left door arc
                px_left = center_x_left + arc_radius * math.cos(angle_rad)
                py_left = center_y_left + arc_radius * math.sin(angle_rad)
                arc_points_left.extend([px_left, py_left])
                # Right door arc
                px_right = center_x_right - arc_radius * math.cos(angle_rad)
                py_right = center_y_right + arc_radius * math.sin(angle_rad)
                arc_points_right.extend([px_right, py_right])
            if len(arc_points_left) >= 4:
                self.elements_layer.add(Line(points=arc_points_left, width=2))
            if len(arc_points_right) >= 4:
                self.elements_layer.add(Line(points=arc_points_right, width=2))

            # Handles
            handle_r = dp(2)
            handle_x_left = x + door_width/4 - dp(2)
            handle_x_right = x + 3*door_width/4 + dp(2)
            handle_y = y + door_height / 2
            self.elements_layer.add(Color(0, 0, 0, 1)) # Black
            self.elements_layer.add(Ellipse(pos=(handle_x_left - handle_r, handle_y - handle_r), size=(2 * handle_r, 2 * handle_r)))
            self.elements_layer.add(Ellipse(pos=(handle_x_right - handle_r, handle_y - handle_r), size=(2 * handle_r, 2 * handle_r)))

        elif etype == "window":
            self.elements_layer.add(Line(points=[x, y + height / 2, x + width, y + height / 2], width=4))

        elif etype == "shower":
            self.elements_layer.add(Line(rectangle=(x, y, width, height), width=2))
            self.elements_layer.add(Line(points=[x, y, x + width, y + height], width=1))
            self.elements_layer.add(Line(points=[x + width, y, x, y + height], width=1))
            circle_r = dp(8)
            self.elements_layer.add(Ellipse(pos=(x + width / 2 - circle_r, y + height / 2 - circle_r), size=(2 * circle_r, 2 * circle_r), width=1))

        elif etype == "flat-tv":
            self.elements_layer.add(Color(0, 0, 0, 1)) # Black screen
            self.elements_layer.add(Rectangle(pos=(x, y), size=(width, height)))

            # Bracket
            bracket_y_offset = dp(8)
            bracket_points = [
                x + width / 2, y + height,
                x + width / 2 - dp(10), y + height + bracket_y_offset,
                x + width / 2 + dp(10), y + height + bracket_y_offset
            ]
            # Kivy Line for polygon outline
            self.elements_layer.add(Color(0, 0, 0, 1))
            # Close the triangle by repeating the first point
            bracket_points_closed = bracket_points + [bracket_points[0], bracket_points[1]]
            self.elements_layer.add(Line(points=bracket_points_closed, width=1, close=True))

        elif etype == "gas-stove":
            self.elements_layer.add(Line(rectangle=(x, y, width, height), width=2))
            burner_r = dp(6)
            burner_pad = burner_r + dp(5)
            points_list = [
                (x + width / 4, y + height / 4),
                (x + 3 * width / 4, y + height / 4),
                (x + width / 4, y + 3 * height / 4),
                (x + 3 * width / 4, y + 3 * height / 4)
            ]
            for bx, by in points_list:
                self.elements_layer.add(Ellipse(pos=(bx - burner_r, by - burner_r), size=(2 * burner_r, 2 * burner_r), width=1))

        elif etype == "side-table":
            self.elements_layer.add(Line(rectangle=(x, y, width, height), width=2))

        elif etype == "bathtub":
            self.elements_layer.add(Line(rectangle=(x, y, width, height), width=2))
            oval_pad = dp(8)
            self.elements_layer.add(Ellipse(pos=(x + oval_pad, y + oval_pad), size=(width - 2 * oval_pad, height - 2 * oval_pad), width=1))

            faucet_r = dp(4)
            faucet_x = x + width - dp(15)
            faucet_y = y + dp(10)
            self.elements_layer.add(Ellipse(pos=(faucet_x - faucet_r, faucet_y - faucet_r), size=(2 * faucet_r, 2 * faucet_r), width=1))
            self.elements_layer.add(Line(points=[faucet_x, faucet_y + faucet_r, faucet_x, faucet_y + faucet_r + dp(6)], width=1))

        else:
            self.elements_layer.add(Line(rectangle=(x, y, width, height), width=2))

    def draw_selection(self):
        self.selection_layer.clear()
        selected_element = self.designer_logic.selected_element
        if not selected_element:
            return

        element_type = selected_element.get("type")
        self.selection_layer.add(Color(0, 0, 1, 1)) # Blue

        if element_type in ["room", "houseBorder"]:
            x, y, w, h = selected_element["x"], selected_element["y"], selected_element["width"], selected_element["height"]
            self.selection_layer.add(Line(rectangle=(x - dp(2), y - dp(2), w + dp(4), h + dp(4)), width=2, dash_offset=5, dash_length=5))
        elif element_type == "wall":
            x1, y1, x2, y2 = selected_element["x1"], selected_element["y1"], selected_element["x2"], selected_element["y2"]
            self.selection_layer.add(Line(points=[x1, y1, x2, y2], width=3, dash_offset=5, dash_length=5))
        else: # Appliances
            size = self.designer_logic.get_appliance_size(element_type)
            width, height = size["width"], size["height"]
            x, y = selected_element["x"], selected_element["y"]
            self.selection_layer.add(Line(rectangle=(x - dp(2), y - dp(2), width + dp(4), height + dp(4)), width=2, dash_offset=5, dash_length=5))

        # Draw resize handles if it's a resizable type
        if selected_element.get("type") in ["room", "houseBorder"]:
             self.draw_resize_handles(selected_element)

    def draw_resize_handles(self, element):
         handle_size = dp(5)
         x1, y1 = element["x"], element["y"]
         x2, y2 = x1 + element["width"], y1 + element["height"]
         handles = [
             (x1, y1), ((x1+x2)/2, y1), (x2, y1),
             (x2, (y1+y2)/2), (x2, y2), ((x1+x2)/2, y2),
             (x1, y2), (x1, (y1+y2)/2)
         ]
         self.selection_layer.add(Color(1, 1, 1, 1)) # White fill
         for hx, hy in handles:

             self.selection_layer.add(Rectangle(pos=(hx - handle_size, hy - handle_size), size=(2 * handle_size, 2 * handle_size)))
         self.selection_layer.add(Color(0, 0, 0, 1)) # Black outline
         for hx, hy in handles:
             # Add outline for handle
             self.selection_layer.add(Line(rectangle=(hx - handle_size, hy - handle_size, 2 * handle_size, 2 * handle_size), width=1))

    def on_touch_down(self, touch):

        if self.collide_point(*touch.pos):

            local_x, local_y = self.to_local(*touch.pos)

            self.touch_start_pos = (local_x, local_y)



            if getattr(self.designer_logic, 'deleting', False):
                clicked_element = self.find_element_at(local_x, local_y)
                if clicked_element and clicked_element in self.designer_logic.elements:

                    element_key = id(clicked_element)
                    if element_key in self.text_labels:
                        label_to_remove = self.text_labels.pop(element_key)
                        if label_to_remove.parent is self:
                            self.remove_widget(label_to_remove)


                    # Remove the element from the list
                    self.designer_logic.elements.remove(clicked_element)

                    # Clear selection if the deleted element was selected
                    if self.designer_logic.selected_element is clicked_element:
                        self.designer_logic.selected_element = None

                    self.designer_logic.save_history() # Save state after deletion
                    self.redraw()
                    return True # Consume the touch

                # If nothing was deleted, maybe deselect?
                elif not clicked_element: # Clicked on empty space while in delete mode
                     self.designer_logic.selected_element = None
                     self.redraw()
                     return True # Consume the touch

            # Check for resizing handles first (if element selected and resizable)
            if self.designer_logic.selected_element and self.designer_logic.selected_element.get("type") in ["room",
                                                                                                             "houseBorder"]:

                handle = self.get_resize_handle(local_x, local_y, self.designer_logic.selected_element)

                if handle:
                    self.resizing_corner = handle

                    if "x" in self.designer_logic.selected_element and "y" in self.designer_logic.selected_element:
                        self.element_start_x = self.designer_logic.selected_element["x"]
                        self.element_start_y = self.designer_logic.selected_element["y"]
                    else:

                        print(f"Warning: Selected element missing 'x' or 'y': {self.designer_logic.selected_element}")

                    if "width" in self.designer_logic.selected_element and "height" in self.designer_logic.selected_element:
                        self.element_start_width = self.designer_logic.selected_element["width"]
                        self.element_start_height = self.designer_logic.selected_element["height"]
                    else:

                        print(
                            f"Warning: Selected element missing 'width' or 'height' for resizing: {self.designer_logic.selected_element}")
                        self.resizing_corner = None  # Cancel resizing attempt

                    return True

            # Wall placement
            if self.designer_logic.placing_wall:
                if not self.designer_logic.wall_start_point:

                    self.designer_logic.wall_start_point = (local_x, local_y)

                else:
                    self.designer_logic.elements.append({
                        "type": "wall",
                        "x1": self.designer_logic.wall_start_point[0],
                        "y1": self.designer_logic.wall_start_point[1],
                        "x2": local_x,
                        "y2": local_y
                    })
                    self.designer_logic.wall_start_point = None
                    self.designer_logic.placing_wall = False
                    self.designer_logic.save_history()
                    self.redraw()
                return True

            # Appliance or element placement
            if self.designer_logic.placing_type:
                self.designer_logic.elements.append({
                    "type": self.designer_logic.placing_type,
                    "x": local_x,
                    "y": local_y,
                    "rotation": self.designer_logic.rotation
                })
                # Reset placing type after placement to stop continuous adding
                self.designer_logic.placing_type = None # <--- UNCOMMENTED THIS LINE ---
                self.designer_logic.save_history()
                self.redraw()
                return True


            clicked_element = self.find_element_at(local_x, local_y)

            if clicked_element:

                if clicked_element.get("type") == "wall":
                    self.designer_logic.selected_element = clicked_element
                    self.dragging_element = None  # Walls can't be dragged
                    self.redraw()
                    return True
                elif "x" not in clicked_element or "y" not in clicked_element:
                    print(f"Warning: Clicked element missing 'x' or 'y', cannot drag: {clicked_element}")

                    self.designer_logic.selected_element = None
                    self.redraw()
                    return True

                self.designer_logic.selected_element = clicked_element
                self.dragging_element = clicked_element

                self.element_start_x = clicked_element["x"]
                self.element_start_y = clicked_element["y"]
                # --- END FIX ---
                self.redraw()
                return True
            else:
                # Clicked on empty space, deselect
                self.designer_logic.selected_element = None
                self.dragging_element = None
                self.resizing_corner = None
                self.redraw()
                return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):

        if self.collide_point(*touch.pos):

            local_x, local_y = self.to_local(*touch.pos)

            dx = local_x - self.touch_start_pos[0]
            dy = local_y - self.touch_start_pos[1]


            # Resizing
            if self.resizing_corner and self.designer_logic.selected_element:
                self.resize_element(self.designer_logic.selected_element, self.resizing_corner, dx, dy)
                self.redraw()
                return True

            # Dragging
            if self.dragging_element:

                if "x" in self.dragging_element and "y" in self.dragging_element:
                    self.dragging_element["x"] = self.element_start_x + dx
                    self.dragging_element["y"] = self.element_start_y + dy
                    self.redraw()
                else:
                    print(f"Warning: Dragging element missing 'x' or 'y': {self.dragging_element}")
                    self.dragging_element = None  # Stop dragging
            return True

            # Wall placement preview
            if self.designer_logic.placing_wall and self.designer_logic.wall_start_point:
                self.preview_layer.clear()
                self.preview_layer.add(Color(0, 0, 1, 1))  # Blue preview
                # --- FIX: Use local coordinates for preview line ---
                self.preview_layer.add(Line(
                    points=[self.designer_logic.wall_start_point[0], self.designer_logic.wall_start_point[1], local_x,
                            local_y], width=2, dash_offset=2, dash_length=2))
                # --- END FIX ---
                return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):

        if self.collide_point(*touch.pos):

            if self.dragging_element or self.resizing_corner:
                self.designer_logic.save_history()
                # Update scroll region if implemented

            # Reset dragging/resizing states
            self.dragging_element = None
            self.resizing_corner = None

            # Clear preview layer
            self.preview_layer.clear()
            self.redraw() # Final redraw
            return True
        return super().on_touch_up(touch)


    def find_element_at(self, x, y):

        for element in reversed(self.designer_logic.elements):
            if element.get("type") in ["room", "houseBorder"]:
                if (element["x"] <= x <= element["x"] + element["width"] and
                        element["y"] <= y <= element["y"] + element["height"]):
                    return element
            elif element.get("type") == "wall":
                # Simple distance check for line
                x1, y1, x2, y2 = element["x1"], element["y1"], element["x2"], element["y2"]
                distance = self.point_to_line_distance(x, y, x1, y1, x2, y2)
                if distance < dp(10):  # Increased threshold for easier selection
                    return element
            elif element.get("type") == "text":  # <--- Check for "text" type here
                # Use the element's defined size for hit testing
                size = element.get("customSize", self.designer_logic.get_appliance_size(element["type"]))
                width, height = size["width"], size["height"]
                if (element["x"] <= x <= element["x"] + width and
                        element["y"] <= y <= element["y"] + height):
                    return element
            # --- End of text check ---
            elif "width" not in element and "height" not in element:  # <--- This elif now correctly belongs to the main chain
                # Note: This block might be obsolete if all elements have size via get_appliance_size
                hit_box_size = dp(10)
                if (element["x"] - hit_box_size <= x <= element["x"] + hit_box_size and
                        element["y"] - hit_box_size <= y <= element["y"] + hit_box_size):
                    return element
            else:  # Appliances (excluding text, and those without width/height)
                # This block now handles all other appliance types
                size = self.designer_logic.get_appliance_size(element["type"])
                width, height = size["width"], size["height"]
                # Consider rotation for hit box? Simplifying.
                if (element["x"] <= x <= element["x"] + width and
                        element["y"] <= y <= element["y"] + height):
                    return element
        return None  # Return None if no element found at (x, y)

    def point_to_line_distance(self, px, py, x1, y1, x2, y2):
        # Calculate distance from point (px, py) to line segment (x1,y1)-(x2,y2)
        A = px - x1
        B = py - y1
        C = x2 - x1
        D = y2 - y1

        dot = A * C + B * D
        len_sq = C * C + D * D
        if len_sq == 0:
             return math.sqrt(A*A + B*B)

        param = dot / len_sq if len_sq != 0 else -1

        if param < 0:
            xx, yy = x1, y1
        elif param > 1:
            xx, yy = x2, y2
        else:
            xx = x1 + param * C
            yy = y1 + param * D

        dx = px - xx
        dy = py - yy
        return math.sqrt(dx * dx + dy * dy)

    def get_resize_handle(self, x, y, element):
        handle_size = dp(5)
        x1, y1 = element["x"], element["y"]
        x2, y2 = x1 + element["width"], y1 + element["height"]
        handles = {
            "nw": (x1, y1),
            "n": ((x1+x2)/2, y1),
            "ne": (x2, y1),
            "e": (x2, (y1+y2)/2),
            "se": (x2, y2),
            "s": ((x1+x2)/2, y2),
            "sw": (x1, y2),
            "w": (x1, (y1+y2)/2),
        }
        for handle_name, (hx, hy) in handles.items():
            if (hx - handle_size <= x <= hx + handle_size and
                hy - handle_size <= y <= hy + handle_size):
                return handle_name
        return None

    def resize_element(self, element, handle, dx, dy):
        x, y, w, h = self.element_start_x, self.element_start_y, self.element_start_width, self.element_start_height
        new_x, new_y, new_w, new_h = x, y, w, h

        if handle == "nw":
            new_x = x + dx
            new_y = y + dy
            new_w = w - dx
            new_h = h - dy
        elif handle == "n":
            new_y = y + dy
            new_h = h - dy
        elif handle == "ne":
            new_y = y + dy
            new_w = w + dx
            new_h = h - dy
        elif handle == "e":
            new_w = w + dx
        elif handle == "se":
            new_w = w + dx
            new_h = h + dy
        elif handle == "s":
            new_h = h + dy
        elif handle == "sw":
            new_x = x + dx
            new_w = w - dx
            new_h = h + dy
        elif handle == "w":
            new_x = x + dx
            new_w = w - dx

        # Ensure minimum size
        min_size = dp(10)
        if new_w < min_size:
            if handle in ["nw", "w", "sw"]:
                new_x = x + w - min_size
            new_w = min_size
        if new_h < min_size:
            if handle in ["nw", "n", "ne"]:
                new_y = y + h - min_size
            new_h = min_size

        # Update element
        element["x"] = new_x
        element["y"] = new_y
        element["width"] = new_w
        element["height"] = new_h