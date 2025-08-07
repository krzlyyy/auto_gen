from kivy.app import App
import json
import os
import re
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.filechooser import FileChooserListView, platform
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from floorplan_designer import FloorPlanDesignerLogic
from widgets import FloorPlanCanvas

try:
    import pytesseract
    from PIL import Image


    if os.name == 'nt':
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    OCR_AVAILABLE = True
    print("OCR libraries loaded successfully. Tesseract path set.")
except ImportError as e:
    print(f"Warning: OCR libraries not found. OCR functionality will be disabled. Error: {e}")
    OCR_AVAILABLE = False
# --- End Import for OCR ---

class ToolSection(BoxLayout):
    """Represents a collapsible section in the toolbar."""
    def __init__(self, title, content_widget, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=dp(50), **kwargs)
        self.title = title
        self.content_widget = content_widget
        self.is_expanded = False
        # Header Button
        self.header_btn = Button(
            text=f"[b]{title}[/b]  +",  # Use +/− for expand/collapse
            markup=True,
            size_hint_y=None,
            height=dp(40),
            background_color=(0.29, 0.43, 0.65, 1)  # #4a6fa5
        )
        self.header_btn.bind(on_press=self.toggle_content)
        self.add_widget(self.header_btn)
        # Content Area (initially not added)
        self.content_widget.size_hint_y = None
        # Schedule the initial visibility update for the next frame
        # This ensures self.parent is set
        Clock.schedule_once(lambda dt: self.update_content_visibility(), 0)
    def toggle_content(self, instance):
        self.is_expanded = not self.is_expanded
        self.update_content_visibility()
        # Update parent scrollview if needed (optional, Kivy usually handles it)
        # parent_sv = self.parent
        # while parent_sv and not isinstance(parent_sv, ScrollView):
        #     parent_sv = parent_sv.parent
        # if parent_sv:
        #     Clock.schedule_once(lambda dt: parent_sv.update_from_scroll(), 0.1)
    def update_content_visibility(self):
        # --- Fix: Check if parent exists ---
        if self.is_expanded:
            if self.content_widget not in self.children:
                self.add_widget(self.content_widget)
                # Set a default or estimated height for now
                self.content_widget.height = dp(200)  # Placeholder, adjust as needed
            self.header_btn.text = f"[b]{self.title}[/b]  −"
            self.height = dp(40) + self.content_widget.height
        else:
            if self.content_widget in self.children:
                self.remove_widget(self.content_widget)
            self.header_btn.text = f"[b]{self.title}[/b]  +"
            self.height = dp(40)
        # The parent (GridLayout in NavigationToolbar) should automatically adjust
        # its height because it has size_hint_y=None and
        # self.layout.bind(minimum_height=self.layout.setter('height'))
        # --- End Fix ---
class NavigationToolbar(ScrollView):
    """Vertical scrollable toolbar containing tool sections."""
    def __init__(self, designer_logic, canvas_widget, **kwargs):
        super().__init__(size_hint=(None, 1), width=dp(250), **kwargs)  # Fixed width
        self.designer_logic = designer_logic
        self.canvas_widget = canvas_widget
        self.bar_width = dp(10)  # Scrollbar width
        self.layout = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        self.layout.bind(minimum_height=self.layout.setter('height'))
        self.add_widget(self.layout)
        self.create_sections()
    def create_sections(self):
        self.layout.clear_widgets()
        # --- Room Dimensions Section ---
        dim_layout = GridLayout(cols=2, spacing=dp(5), size_hint_y=None, height=dp(120))
        labels = ["X (m):", "Y (m):", "Width (m):", "Height (m):"]
        # Set default values for X and Y to center of canvas
        # Default width and height will be 5 and 3.75 respectively
        defaults = ["7", "3", "15", "10.75"]
        self.dim_entries = []
        for i, label in enumerate(labels):
            lbl = Label(text=label, size_hint_x=0.4, halign='right', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))  # For text wrapping/alignment
            entry = TextInput(text=defaults[i], size_hint_x=0.6, multiline=False)
            dim_layout.add_widget(lbl)
            dim_layout.add_widget(entry)
            self.dim_entries.append(entry)
        btn_layout = GridLayout(cols=3, spacing=dp(5), size_hint_y=None, height=dp(40))
        btn_add_room = Button(text="Add Room")
        btn_add_border = Button(text="Add Border")
        btn_add_wall = Button(text="Add Wall")
        btn_add_room.bind(on_press=self.on_add_room)
        btn_add_border.bind(on_press=self.on_add_border)
        btn_add_wall.bind(on_press=self.on_start_wall_placement)
        btn_layout.add_widget(btn_add_room)
        btn_layout.add_widget(btn_add_border)
        btn_layout.add_widget(btn_add_wall)
        dim_section_layout = BoxLayout(orientation='vertical', spacing=dp(5))
        dim_section_layout.add_widget(dim_layout)
        dim_section_layout.add_widget(btn_layout)
        dim_section = ToolSection("Room Dimensions", dim_section_layout)
        self.layout.add_widget(dim_section)
        # ---
        # --- Appliances Section ---
        appliance_dropdown = DropDown()
        appliances = [
            "Single Bed", "Double Bed", "Queen Bed", "King Bed",
            "Dining Table", "Sofa", "Fridge", "Sink", "Toilet", "Door", "Double Door", "Window",
            "Shower", "Flat TV", "Gas Stove", "Side Table", "Bathtub"
        ]
        self.appliance_map = {
            "Single Bed": "bed-single", "Double Bed": "bed-double", "Queen Bed": "bed-queen", "King Bed": "bed-king",
            "Dining Table": "table", "Sofa": "sofa", "Fridge": "fridge", "Sink": "sink", "Toilet": "toilet",
            "Door": "door", "Double Door": "double-door", "Window": "window", "Shower": "shower", "Flat TV": "flat-tv",
            "Gas Stove": "gas-stove", "Side Table": "side-table", "Bathtub": "bathtub"
        }
        for app in appliances:
            btn = Button(text=app, size_hint_y=None, height=dp(40))
            btn.bind(on_release=lambda btn_instance: self.on_appliance_selected(btn_instance.text))
            appliance_dropdown.add_widget(btn)
        appliance_mainbutton = Button(text='--Select Appliance--', size_hint_y=None, height=dp(40))
        appliance_mainbutton.bind(on_release=appliance_dropdown.open)
        appliance_dropdown.bind(on_select=lambda instance, x: setattr(appliance_mainbutton, 'text', x))
        appliance_section = ToolSection("Add Appliances", appliance_mainbutton)
        self.layout.add_widget(appliance_section)
        # ---
        # --- Edit Tools Section ---
        edit_layout = GridLayout(cols=2, spacing=dp(5), size_hint_y=None, height=dp(100))  # Height adjusted
        btn_rotate = Button(text="Rotate")
        btn_delete = Button(text="Delete")
        btn_undo = Button(text="Undo")
        btn_redo = Button(text="Redo")
        btn_add_text = Button(text="Add Text")  # <-- Add Text Button is HERE
        btn_rotate.bind(on_press=self.on_rotate)
        btn_delete.bind(on_press=self.on_delete)
        btn_undo.bind(on_press=self.on_undo)
        btn_redo.bind(on_press=self.on_redo)
        # --- Bind the Add Text button ---
        btn_add_text.bind(on_press=self.on_add_text)  # <-- Handler bound HERE
        # ---
        edit_layout.add_widget(btn_rotate)
        edit_layout.add_widget(btn_delete)
        edit_layout.add_widget(btn_undo)
        edit_layout.add_widget(btn_redo)
        edit_layout.add_widget(btn_add_text)  # <-- Button added to layout HERE
        edit_section = ToolSection("Edit Tools", edit_layout)
        self.layout.add_widget(edit_section)
        # ---
        # --- File Operations Section ---
        # Updated with actual functionality
        file_layout = BoxLayout(orientation='horizontal', spacing=dp(5), size_hint_y=None, height=dp(50))
        btn_save = Button(text="Save", size_hint_y=None, height=dp(40))
        btn_import = Button(text="Import", size_hint_y=None, height=dp(40))
        btn_save.bind(on_press=self.on_save)
        btn_import.bind(on_press=self.on_import)
        file_layout.add_widget(btn_save)
        file_layout.add_widget(btn_import)
        file_section = ToolSection("File Operations", file_layout)
        self.layout.add_widget(file_section)
        # ---
        # --- Generate Section ---
        gen_btn = Button(text="Generate Floor Plan", size_hint_y=None, height=dp(50))
        gen_btn.bind(on_press=self.on_generate)
        gen_section = ToolSection("Generate", gen_btn)
        self.layout.add_widget(gen_section)
        # ---
        # --- Presets Section ---
        preset_layout = GridLayout(cols=2, spacing=dp(5), size_hint_y=None, height=dp(100))
        btn_room_preset = Button(text="Insert Room")
        btn_kitchen_preset = Button(text="Insert Kitchen")
        btn_living_preset = Button(text="Living Room")
        btn_bath_preset = Button(text="Bathroom")
        btn_room_preset.bind(on_press=lambda x: self.on_add_preset("room"))
        btn_kitchen_preset.bind(on_press=lambda x: self.on_add_preset("kitchen"))
        btn_living_preset.bind(on_press=lambda x: self.on_add_preset("livingroom"))
        btn_bath_preset.bind(on_press=lambda x: self.on_add_preset("bathroom"))
        preset_layout.add_widget(btn_room_preset)
        preset_layout.add_widget(btn_kitchen_preset)
        preset_layout.add_widget(btn_living_preset)
        preset_layout.add_widget(btn_bath_preset)
        preset_section = ToolSection("Room Presets (Fixed Size)", preset_layout)
        self.layout.add_widget(preset_section)
        # ---
        # --- Image Scanning Section ---
        scan_btn = Button(text="Scan Image", size_hint_y=None, height=dp(50))
        scan_btn.bind(on_press=self.on_scan_image)
        scan_section = ToolSection("Image Scanning", scan_btn)
        self.layout.add_widget(scan_section)
        # ---
    # --- Event Handlers calling logic from designer_logic ---
    # In main.py, modify the on_add_room method:
    def on_add_room(self, instance):
        try:
            # Get x, y, width, height from inputs
            x_meters = float(self.dim_entries[0].text)
            y_meters = float(self.dim_entries[1].text)
            width_meters = float(self.dim_entries[2].text)
            height_meters = float(self.dim_entries[3].text)
            # Validate minimum room size
            if width_meters < 5 or height_meters < 3.75:
                self.show_popup("Room Size Error",
                                "Room size is too small! Width must be at least 5 meters and height must be at least 3.75 meters.")
                return
            # Convert meters to pixels
            x = self.designer_logic.meters_to_pixels(x_meters)
            y = self.designer_logic.meters_to_pixels(y_meters)
            width = self.designer_logic.meters_to_pixels(width_meters)
            height = self.designer_logic.meters_to_pixels(height_meters)
            # Add room using provided coordinates
            self.designer_logic.add_room(x, y, width, height)
            self.canvas_widget.redraw()
        except ValueError:
            popup = Popup(title='Error', content=Label(text='Invalid dimensions'), size_hint=(0.6, 0.4))
            popup.open()
    def on_add_border(self, instance):
        try:
            # Get x, y, width, height from inputs
            x_meters = float(self.dim_entries[0].text)
            y_meters = float(self.dim_entries[1].text)
            width_meters = float(self.dim_entries[2].text)
            height_meters = float(self.dim_entries[3].text)
            # Validate minimum room size
            if width_meters < 5 or height_meters < 3.75:
                self.show_popup("Room Size Error",
                                "Room size is too small! Width must be at least 5 meters and height must be at least 3.75 meters.")
                return
            # Convert meters to pixels
            x = self.designer_logic.meters_to_pixels(x_meters)
            y = self.designer_logic.meters_to_pixels(y_meters)
            width = self.designer_logic.meters_to_pixels(width_meters)
            height = self.designer_logic.meters_to_pixels(height_meters)
            # Add border using provided coordinates
            self.designer_logic.add_house_border(x, y, width, height)
            self.canvas_widget.redraw()
        except ValueError:
            popup = Popup(title='Error', content=Label(text='Invalid dimensions'), size_hint=(0.6, 0.4))
            popup.open()
    def on_start_wall_placement(self, instance):
        self.designer_logic.start_wall_placement()
        self.canvas_widget.redraw()  # Update UI state indication if needed

    def on_add_text(self, instance):
        # Create a text input dialog with better proportions
        popup_layout = BoxLayout(
            orientation='vertical',
            padding=dp(10),
            spacing=dp(10),
            size_hint=(1, 1)
        )

        # Text input (comfortable size)
        popup_layout.add_widget(Label(
            text="Enter Text:",
            size_hint_y=None,
            height=dp(20),
            font_size='14sp'
        ))

        text_input = TextInput(
            text="",
            multiline=True,
            size_hint_y=None,
            height=dp(60),  # More space for text
            font_size='14sp'
        )
        popup_layout.add_widget(text_input)

        # Font size slider with value display
        font_size_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40),
            spacing=dp(10)
        )

        font_size_layout.add_widget(Label(
            text="Font Size:",
            size_hint_x=None,
            width=dp(80),
            font_size='14sp'
        ))

        font_size_slider = Slider(
            min=8,
            max=72,
            value=14,
            size_hint_x=0.6,
            step=1
        )

        font_size_value = Label(
            text="14",
            size_hint_x=0.2,
            text_size=(dp(40), None),
            halign='right',
            valign='middle',
            font_size='14sp'
        )

        def update_font_size(instance, value):
            font_size_value.text = str(int(value))

        font_size_slider.bind(value=update_font_size)
        font_size_layout.add_widget(font_size_slider)
        font_size_layout.add_widget(font_size_value)
        popup_layout.add_widget(font_size_layout)

        # Buttons (comfortable size)
        button_layout = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )
        save_btn = Button(
            text="Save",
            font_size='14sp'
        )
        cancel_btn = Button(
            text="Cancel",
            font_size='14sp'
        )
        button_layout.add_widget(save_btn)
        button_layout.add_widget(cancel_btn)
        popup_layout.add_widget(button_layout)

        # Create popup with better size
        popup = Popup(
            title="Add Text",
            content=popup_layout,
            size_hint=(None, None),
            size=(dp(320), dp(250))  # More comfortable dimensions
        )

        # Save button action
        def save_text(instance):
            if not text_input.text.strip():
                return  # Don't save empty text

            text = text_input.text
            font_size = int(font_size_slider.value)
            x = self.canvas_widget.width // 2
            y = self.canvas_widget.height // 2

            self.designer_logic.elements.append({
                "type": "text",
                "x": x,
                "y": y,
                "width": 200,
                "height": 40,
                "content": text,
                "fontSize": font_size
            })

            self.designer_logic.save_history()
            self.canvas_widget.redraw()
            popup.dismiss()

        save_btn.bind(on_press=save_text)
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()

    def on_edit_text(self, instance):
        if not self.designer_logic.selected_element:
            self.show_popup("No Selection", "Please select a text element first.")
            return
        element = self.designer_logic.selected_element
        if element.get("type") != "text":
            self.show_popup("Invalid Selection", "Please select a text element to edit.")
            return
        # Create a simpler text editing dialog without color picker
        popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        # Text input
        text_input = TextInput(text=element.get("content", ""), multiline=True)
        popup_layout.add_widget(Label(text="Edit Text:", size_hint_y=None, height=dp(30)))
        popup_layout.add_widget(text_input)
        # Font size slider
        font_size_slider = Slider(min=8, max=72, value=element.get("fontSize", 14), orientation='horizontal')
        popup_layout.add_widget(Label(text="Font Size:", size_hint_y=None, height=dp(30)))
        popup_layout.add_widget(font_size_slider)
        # Buttons
        button_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=10)
        save_btn = Button(text="Save", size_hint_x=0.5)
        cancel_btn = Button(text="Cancel", size_hint_x=0.5)
        button_layout.add_widget(save_btn)
        button_layout.add_widget(cancel_btn)
        popup_layout.add_widget(button_layout)
        # Create popup
        popup = Popup(title="Edit Text", content=popup_layout, size_hint=(0.8, 0.8))

        # Save button action
        def save_text(instance):
            # Update element with new text and font size
            element["content"] = text_input.text
            element["fontSize"] = int(font_size_slider.value)
            # Remove color property if it exists (to ensure no color picker influence)
            element.pop("color", None)
            self.designer_logic.save_history()
            self.canvas_widget.redraw()
            popup.dismiss()

        save_btn.bind(on_press=save_text)
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()


    def on_appliance_selected(self, appliance_name):
        if appliance_name in self.appliance_map:
            appliance_type = self.appliance_map[appliance_name]
            self.designer_logic.set_placing_type(appliance_type)
            self.canvas_widget.redraw()  # Update UI state indication if needed
            # Show info popup or status
            # status_msg("Select placement point on canvas")
    def on_rotate(self, instance):
        self.designer_logic.toggle_rotation()
        self.canvas_widget.redraw()  # Redraw if selection highlight changes
    # --- Updated on_delete ---
    def on_delete(self, instance):
        # Check if something is selected before deleting
        if self.designer_logic.selected_element:
            self.designer_logic.delete_selected()
            self.canvas_widget.redraw()
        else:
            # Show a warning popup if nothing is selected
            popup_content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
            popup_content.add_widget(Label(text="No object is selected to delete.", text_size=(dp(300), None)))
            close_btn = Button(text="Close", size_hint_y=None, height=dp(40))
            popup_content.add_widget(close_btn)
            popup = Popup(title="Warning", content=popup_content, size_hint=(0.8, 0.4))
            close_btn.bind(on_press=popup.dismiss)
            popup.open()
    # --- End Updated on_delete ---
    def on_undo(self, instance):
        self.designer_logic.undo()
        self.canvas_widget.redraw()
    def on_redo(self, instance):
        self.designer_logic.redo()
        self.canvas_widget.redraw()
    # --- Added Save/Import functionality with user file selection ---
    def on_save(self, instance):
        """Opens a file chooser to select where to save the floor plan."""
        # Create popup content
        popup_content = BoxLayout(orientation='vertical')
        # Create FileChooser
        filechooser = FileChooserListView(
            filters=['*.json'],
            path=os.path.expanduser('~') if platform != 'android' else '/'
        )
        # Add a filename input
        filename_layout = BoxLayout(size_hint_y=None, height=dp(50))
        filename_layout.add_widget(Label(text="Filename:", size_hint_x=0.3))
        filename_input = TextInput(text="floorplan.json", size_hint_x=0.7)
        filename_layout.add_widget(filename_input)
        popup_content.add_widget(filechooser)
        popup_content.add_widget(filename_layout)
        # Button layout
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        btn_save = Button(text="Save")
        btn_cancel = Button(text="Cancel")
        popup = Popup(title="Save Floor Plan", content=popup_content, size_hint=(0.9, 0.9))
        def save_file(*args):
            if filechooser.selection:
                selected_dir = filechooser.path
                filename = filename_input.text.strip()
                # Ensure filename has .json extension
                if not filename.endswith('.json'):
                    filename += '.json'
                file_path = os.path.join(selected_dir, filename)
                try:
                    # Prepare data with metadata
                    data_to_save = {
                        'version': '1.0',
                        'created': str(__import__('datetime').datetime.now()),
                        'elements': self.designer_logic.elements,
                        'grid_size': self.designer_logic.grid_size,
                        'meters_to_pixels_factor': self.designer_logic.meters_to_pixels_factor,
                    }
                    # Write to file
                    with open(file_path, 'w') as f:
                        json.dump(data_to_save, f, indent=4)
                    # Show success message
                    self.show_popup("Success", f"Floor plan saved to:\n{file_path}")
                    popup.dismiss()
                except Exception as e:
                    print(f"Error saving file: {e}")
                    self.show_popup("Error", f"Failed to save: {str(e)}")
            else:
                # Try to save in the selected directory even if no file is selected
                selected_dir = filechooser.path
                filename = filename_input.text.strip()
                # Ensure filename has .json extension
                if not filename.endswith('.json'):
                    filename += '.json'
                file_path = os.path.join(selected_dir, filename)
                try:
                    # Prepare data with metadata
                    data_to_save = {
                        'version': '1.0',
                        'created': str(__import__('datetime').datetime.now()),
                        'elements': self.designer_logic.elements,
                        'grid_size': self.designer_logic.grid_size,
                        'meters_to_pixels_factor': self.designer_logic.meters_to_pixels_factor,
                    }
                    # Write to file
                    with open(file_path, 'w') as f:
                        json.dump(data_to_save, f, indent=4)
                    # Show success message
                    self.show_popup("Success", f"Floor plan saved to:\n{file_path}")
                    popup.dismiss()
                except Exception as e:
                    print(f"Error saving file: {e}")
                    self.show_popup("Error", f"Failed to save: {str(e)}")
        def cancel_save(*args):
            popup.dismiss()
        btn_save.bind(on_press=save_file)
        btn_cancel.bind(on_press=cancel_save)
        btn_layout.add_widget(btn_save)
        btn_layout.add_widget(btn_cancel)
        popup_content.add_widget(btn_layout)
        popup.open()
    def on_import(self, instance):
        """Opens a file chooser to select which floor plan to import."""
        # Create popup content
        popup_content = BoxLayout(orientation='vertical')
        # Create FileChooser
        filechooser = FileChooserListView(
            filters=['*.json'],
            path=os.path.expanduser('~') if platform != 'android' else '/'
        )
        popup_content.add_widget(filechooser)
        # Button layout
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        btn_import = Button(text="Import")
        btn_cancel = Button(text="Cancel")
        popup = Popup(title="Import Floor Plan", content=popup_content, size_hint=(0.9, 0.9))
        def import_file(*args):
            if filechooser.selection:
                file_path = filechooser.selection[0]
                try:
                    # Read from file
                    with open(file_path, 'r') as f:
                        loaded_data = json.load(f)
                    # Load data into logic
                    self.designer_logic.elements = loaded_data.get('elements', [])
                    # Restore metadata if available
                    if 'grid_size' in loaded_data:
                        self.designer_logic.grid_size = loaded_data['grid_size']
                    if 'meters_to_pixels_factor' in loaded_data:
                        self.designer_logic.meters_to_pixels_factor = loaded_data['meters_to_pixels_factor']
                    # Reset selection
                    self.designer_logic.selected_element = None
                    # Update UI
                    self.canvas_widget.redraw()
                    self.show_popup("Success", f"Floor plan imported from:\n{file_path}")
                    popup.dismiss()
                except Exception as e:
                    print(f"Error importing file: {e}")
                    self.show_popup("Error", f"Failed to import: {str(e)}")
            else:
                self.show_popup("Error", "Please select a file to import.")
        def cancel_import(*args):
            popup.dismiss()
        btn_import.bind(on_press=import_file)
        btn_cancel.bind(on_press=cancel_import)
        btn_layout.add_widget(btn_import)
        btn_layout.add_widget(btn_cancel)
        popup_content.add_widget(btn_layout)
        popup.open()
    def show_popup(self, title, message):
        """Helper to show a popup message."""
        popup_content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        popup_content.add_widget(Label(text=message, text_size=(dp(300), None)))
        close_btn = Button(text="Close", size_hint_y=None, height=dp(40))
        popup_content.add_widget(close_btn)
        popup = Popup(title=title, content=popup_content, size_hint=(0.8, 0.4))
        close_btn.bind(on_press=popup.dismiss)
        popup.open()
    # --- End Added Save/Import functionality ---
    # --- Add show_room_too_small_popup method ---
    def show_room_too_small_popup(self, room_name="House"):
        """Show popup message when room/house is too small for generation."""
        # Create popup content
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        # Create label with message
        message_label = Label(
            text=f"The {room_name} is too small! Please adjust the room size.\nWidth must be at least 15m and Height at least 10.75m.",
            size_hint_y=None,
            # Adjust height and text_size for the longer message
            height=dp(70),
            text_size=(dp(300), None) # Allow text wrapping
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

    def on_generate(self, instance):
        try:

            x_meters_str = self.dim_entries[0].text.strip()
            y_meters_str = self.dim_entries[1].text.strip()
            width_meters_str = self.dim_entries[2].text.strip()
            height_meters_str = self.dim_entries[3].text.strip()

            # Handle potential empty strings after strip, defaulting to "0" for coords, and existing defaults for size if somehow cleared
            x_meters = float(x_meters_str) if x_meters_str else 0.0
            y_meters = float(y_meters_str) if y_meters_str else 0.0
            width_meters = float(width_meters_str) if width_meters_str else 15.0   # Default from UI if somehow empty
            height_meters = float(height_meters_str) if height_meters_str else 10.75 # Default from UI if somehow empty

            min_width_m = 15.0
            min_height_m = 10.75

            if width_meters < min_width_m or height_meters < min_height_m:
                # If the specified area is too small, show the specific popup
                self.show_room_too_small_popup("House Area")
                # Stop the generation process
                return

            # Convert meters to pixels for the designer logic
            house_x_px = self.designer_logic.meters_to_pixels(x_meters)
            house_y_px = self.designer_logic.meters_to_pixels(y_meters)
            house_width_px = self.designer_logic.meters_to_pixels(width_meters)
            house_height_px = self.designer_logic.meters_to_pixels(height_meters)

            self.designer_logic.generate_floor_plan(house_x_px, house_y_px, house_width_px, house_height_px)

            self.canvas_widget.redraw()

        except ValueError:
            # Handle case where text input cannot be converted to float
            self.show_popup("Error", "Invalid dimensions for generation. Please enter valid numbers.")
        except Exception as e:
            # Handle other unexpected errors during generation
            print(f"Error during floor plan generation: {e}")
            import traceback
            traceback.print_exc() # Print full error details to console
            self.show_popup("Generation Error", f"An error occurred during generation: {str(e)}")

    def on_add_preset(self, preset_type):
        self.designer_logic.add_preset(preset_type)
        self.canvas_widget.redraw()

    def on_scan_image(self, instance):
        """Opens a file chooser to select an image for scanning."""
        # Create popup content
        popup_content = BoxLayout(orientation='vertical')

        # Filter for common image types
        filechooser = FileChooserListView(filters=['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff'])
        # Set initial path (adjust as needed)
        if platform == 'android':
            pass
        else:
            filechooser.path = os.path.expanduser('~')  # Start in home directory
        popup_content.add_widget(filechooser)
        # Button layout
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        btn_select = Button(text="Select")
        btn_cancel = Button(text="Cancel")
        popup = Popup(title="Select Image to Scan", content=popup_content, size_hint=(0.9, 0.9))
        def select_image(*args):
            if filechooser.selection:
                selected_path = filechooser.selection[0]
                popup.dismiss()
                # Call the actual scanning logic (placeholder for now)
                self.process_scanned_image(selected_path)
            else:
                # Show warning or do nothing
                # Optional: self.show_popup("Warning", "No file selected.")
                pass
        def cancel_selection(*args):
            popup.dismiss()
        btn_select.bind(on_press=select_image)
        btn_cancel.bind(on_press=cancel_selection)
        btn_layout.add_widget(btn_select)
        btn_layout.add_widget(btn_cancel)
        popup_content.add_widget(btn_layout)
        popup.open()
    # --- Updated process_scanned_image with OCR for 4 numbers ---
    def process_scanned_image(self, image_path):
        """Processes the selected scanned image to extract up to 4 dimensions (x, y, width, height) in order."""
        try:
            # --- Attempt OCR First ---
            if OCR_AVAILABLE:
                try:
                    # 1. Open the image
                    img = Image.open(image_path)

                    img = img.convert('L')

                    threshold = 150
                    img = img.point(lambda x: 0 if x < threshold else 255, '1')
                    # --------------------------

                    # 2. Perform OCR
                    custom_config = r'--oem 3 --psm 6' # Removed char whitelist to find any digits
                    ocr_text = pytesseract.image_to_string(img, config=custom_config)
                    print(f"DEBUG: OCR Extracted Text:\n{ocr_text}") # Debug output

                    # 3. Parse OCR Text for Numbers
                    number_pattern = re.compile(r'\d+(?:\.\d+)?')

                    # Find all matches in the OCR text
                    all_matches = number_pattern.findall(ocr_text)

                    # Convert string matches to floats
                    extracted_numbers = []
                    for match in all_matches:
                        try:
                            num = float(match)
                            extracted_numbers.append(num)
                        except ValueError:
                            # Ignore if conversion fails (shouldn't happen with the regex, but good practice)
                            pass

                    print(f"DEBUG: Found numbers list: {extracted_numbers}") # Debug print

                    # 4. Assign found numbers or defaults

                    # Initialize defaults
                    x_val = 0.0
                    y_val = 0.0
                    width_val = 0.0
                    height_val = 0.0

                    num_found = len(extracted_numbers)
                    if num_found == 0:
                        # No numbers found
                        pass # Keep defaults
                        self.show_popup("Scan Complete", "Scan completed, but no numbers were found. All dimensions set to 0.")
                    elif num_found == 1:

                        height_val = extracted_numbers[0]
                        self.show_popup("Scan Info", f"Scanner found 1 number. Assuming it's Height={height_val}. Others set to 0.")
                    elif num_found == 2:
                        # Assume first two: Width, Height (common pattern)
                        width_val = extracted_numbers[0]
                        height_val = extracted_numbers[1]
                        self.show_popup("Scan Info", f"Scanner found 2 numbers. Assuming Width={width_val}, Height={height_val}. X, Y set to 0.")
                    elif num_found == 3:

                        x_val = extracted_numbers[0]
                        width_val = extracted_numbers[1]
                        height_val = extracted_numbers[2]
                        self.show_popup("Scan Info", f"Scanner found 3 numbers. Assigned as X={x_val}, Width={width_val}, Height={height_val}. Y set to 0.")
                    elif num_found >= 4:

                        x_val = extracted_numbers[0]
                        y_val = extracted_numbers[1]
                        width_val = extracted_numbers[2]
                        height_val = extracted_numbers[3]
                        if num_found > 4:
                             self.show_popup("Scan Info", f"Scanner found {num_found} numbers. Using the first four: X={x_val}, Y={y_val}, Width={width_val}, Height={height_val}.")
                        else:
                             self.show_popup("Scan Complete", f"Scanned successful. Found four numbers: X={x_val}, Y={y_val}, Width={width_val}, Height={height_val}")

                    # 5. Update UI fields with final values
                    self.dim_entries[0].text = str(x_val)       # X (m)
                    self.dim_entries[1].text = str(y_val)       # Y (m)
                    self.dim_entries[2].text = str(width_val)   # Width (m)
                    self.dim_entries[3].text = str(height_val)  # Height (m)


                except Exception as ocr_error:
                    print(f"Error during scan processing: {ocr_error}")
                    import traceback
                    traceback.print_exc() # Print full traceback for debugging
                    self.show_popup("Scan Error", f"Scan failed: {ocr_error}. Setting all dimensions to 0.")
                    # Set all dimensions to default (0) on OCR error
                    self.dim_entries[0].text = "0"
                    self.dim_entries[1].text = "0"
                    self.dim_entries[2].text = "0"
                    self.dim_entries[3].text = "0"

            else:
                print("OCR library not available.")
                self.show_popup("Scan Error", "OCR library (pytesseract) is not installed or not available. Setting all dimensions to 0.")
                # Set all dimensions to default (0) if OCR not available
                self.dim_entries[0].text = "0"
                self.dim_entries[1].text = "0"
                self.dim_entries[2].text = "0"
                self.dim_entries[3].text = "0"

        except Exception as e:
            print(f"Unexpected error processing scanned image: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging
            self.show_popup("Error", f"Failed to process image: {str(e)}")

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.designer_logic = FloorPlanDesignerLogic()  # Initialize core logic
        # Main Layout
        main_layout = BoxLayout(orientation='horizontal')  # Toolbar left, Canvas right
        # Canvas Area (Right, takes most space)
        self.canvas_widget = FloorPlanCanvas(self.designer_logic)  # Custom widget for drawing
        # Wrap canvas in a ScrollView for panning
        self.canvas_scroll = ScrollView(do_scroll_x=True, do_scroll_y=True, bar_width=dp(10))
        self.canvas_scroll.add_widget(self.canvas_widget)
        # Toolbar (Left, fixed width)
        self.toolbar = NavigationToolbar(self.designer_logic, self.canvas_widget)
        # Status Bar (Bottom of canvas area)
        self.status_bar = Label(
            text="Grid: 20px | Rotation: 0° | Selected: None",
            size_hint_y=None,
            height=dp(30),
            color=(0, 0, 0, 1),
            halign='left',
            valign='middle',
            padding=(dp(10), 0)
        )
        self.status_bar.bind(size=self.status_bar.setter('text_size'))  # For alignment
        # Assemble Canvas Area
        canvas_area_layout = BoxLayout(orientation='vertical')
        canvas_area_layout.add_widget(self.canvas_scroll)
        canvas_area_layout.add_widget(self.status_bar)
        # Add to main layout
        main_layout.add_widget(self.toolbar)
        main_layout.add_widget(canvas_area_layout)
        self.add_widget(main_layout)

    def update_status(self, dt):

        selected_info = "None"
        if self.designer_logic.selected_element:
            selected_info = self.designer_logic.selected_element.get('type', 'Unknown')

        pos_text = "Pos: --, --"
        self.status_bar.text = f"Grid: {self.designer_logic.grid_size}px | Rotation: {self.designer_logic.rotation}° | Selected: {selected_info} | {pos_text}"
class FloorPlanKivyApp(App):
    def build(self):
        self.title = "Auto Gen"
        self.icon = "AutoGen.png"
        return MainScreen()

if __name__ == '__main__':
    FloorPlanKivyApp().run()
