import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as tb
from transformers import T5Tokenizer, T5ForConditionalGeneration
import torch
import re
from PIL import Image, ImageTk
import threading
import time
import math
import random

# Define color palette with the exact shades specified
PRIMARY_COLOR = "#F2EFE7"    # Light cream
SECONDARY_COLOR = "#9ACBD0"  # Soft teal
ACCENT_COLOR = "#48A6A7"     # Medium teal
DARK_COLOR = "#006A71"       # Dark teal
BG_COLOR = "#FFFFFF"         # White background
TEXT_COLOR = "#333333"       # Dark gray for text

# Load the fine-tuned model and tokenizer
model = T5ForConditionalGeneration.from_pretrained('./final_model/final_model')
tokenizer = T5Tokenizer.from_pretrained('./final_model/final_model')

# Set the device for model (GPU or CPU)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Clean Text
def clean_text(text):
    text = text.lower()  
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text

# Function to generate recipe
def generate_recipe(prompt, model, tokenizer, max_length=150):
    prompt = clean_text(prompt)
    inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=128)
    input_ids = inputs['input_ids'].to(device)
    attention_mask = inputs['attention_mask'].to(device)

    output = model.generate(input_ids, attention_mask=attention_mask, max_length=max_length, num_return_sequences=1)
    return tokenizer.decode(output[0], skip_special_tokens=True)

# Helper function to create rounded rectangle in Canvas (missing in the original Canvas class)
def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius=25, **kwargs):
    points = [
        x1+radius, y1,
        x2-radius, y1,
        x2, y1,
        x2, y1+radius,
        x2, y2-radius,
        x2, y2,
        x2-radius, y2,
        x1+radius, y2,
        x1, y2,
        x1, y2-radius,
        x1, y1+radius,
        x1, y1
    ]
    return canvas.create_polygon(points, **kwargs, smooth=True)

# Create main window
app = tb.Window(themename="cosmo")
app.title("DishCrafter - Recipe Generator")
app.geometry("800x700")
app.configure(bg=BG_COLOR)

# Custom styles
style = tb.Style()
style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR)
style.configure("TFrame", background=BG_COLOR)
style.configure("TButton", background=SECONDARY_COLOR, foreground=TEXT_COLOR)
style.configure("RecipeButton.TButton", background=ACCENT_COLOR, foreground="#FFFFFF", font=("Helvetica", 12, "bold"))
style.configure("HeaderFrame.TFrame", background=DARK_COLOR)
style.configure("Header.TLabel", background=DARK_COLOR, foreground="#FFFFFF", font=("Helvetica", 24, "bold"))
style.configure("SubHeader.TLabel", background=DARK_COLOR, foreground="#FFFFFF", font=("Helvetica", 14))

# Create a class for custom rounded button
class RoundedButton(tk.Canvas):
    def __init__(self, parent, width, height, bg_color, text, command=None, text_color="#FFFFFF", font=("Helvetica", 12, "bold")):
        super().__init__(parent, width=width, height=height, bg=BG_COLOR, highlightthickness=0)
        
        self.bg_color = bg_color
        self.bg_color_darker = self._darken_color(bg_color, 0.15)
        self.command = command
        self.width = width
        self.height = height
        
        # Draw rounded rectangle
        self.rounded_rect = create_rounded_rectangle(self, 0, 0, width, height, radius=height//2, fill=bg_color)
        
        # Add text
        self.text_id = self.create_text(width//2, height//2, text=text, fill=text_color, font=font)
        
        # Bind events
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)
    
    def _darken_color(self, hex_color, factor):
        # Convert hex to RGB
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        
        # Darken
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _on_enter(self, event):
        self.itemconfig(self.rounded_rect, fill=self.bg_color_darker)
    
    def _on_leave(self, event):
        self.itemconfig(self.rounded_rect, fill=self.bg_color)
    
    def _on_click(self, event):
        self.itemconfig(self.rounded_rect, fill=self._darken_color(self.bg_color, 0.3))
    
    def _on_release(self, event):
        self.itemconfig(self.rounded_rect, fill=self.bg_color_darker)
        if self.command:
            self.command()
            
    def config(self, **kwargs):
        if "command" in kwargs:
            self.command = kwargs["command"]
        if "text" in kwargs:
            self.itemconfig(self.text_id, text=kwargs["text"])
        if "bg" in kwargs:
            self.bg_color = kwargs["bg"]
            self.bg_color_darker = self._darken_color(kwargs["bg"], 0.15)
            self.itemconfig(self.rounded_rect, fill=kwargs["bg"])

# Loading animation class
class LoadingAnimation:
    def __init__(self, canvas):
        self.canvas = canvas
        self.running = False
        self.dots = []
        self.colors = [PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR, DARK_COLOR]
        
    def start(self):
        self.running = True
        self.canvas.delete("all")
        self.dots = []
        centerx = self.canvas.winfo_width() // 2
        centery = self.canvas.winfo_height() // 2
        radius = min(centerx, centery) - 10
        
        for i in range(8):
            angle = i * (360 / 8)
            x = centerx + radius * 0.7 * round(math.cos(math.radians(angle)), 2)
            y = centery + radius * 0.7 * round(math.sin(math.radians(angle)), 2)
            dot = self.canvas.create_oval(x-5, y-5, x+5, y+5, fill=random.choice(self.colors))
            self.dots.append((dot, angle))
        
        threading.Thread(target=self._animate, daemon=True).start()
    
    def _animate(self):
        step = 0
        while self.running:
            for dot, base_angle in self.dots:
                angle = base_angle + step
                centerx = self.canvas.winfo_width() // 2
                centery = self.canvas.winfo_height() // 2
                radius = min(centerx, centery) - 10
                
                x = centerx + radius * 0.7 * round(math.cos(math.radians(angle)), 2)
                y = centery + radius * 0.7 * round(math.sin(math.radians(angle)), 2)
                
                self.canvas.coords(dot, x-5, y-5, x+5, y+5)
            
            step += 10
            time.sleep(0.05)
            try:
                self.canvas.update()
            except:
                self.running = False
    
    def stop(self):
        self.running = False
        self.canvas.delete("all")

# Function to handle button click with animation
def on_generate():
    prompt = prompt_entry.get()
    if not prompt.strip():
        messagebox.showwarning("Warning", "Please enter a recipe prompt.")
        return
    
    # Start loading animation
    result_text.config(state="normal")
    result_text.delete(1.0, "end")
    result_text.insert("end", "Generating your recipe...")
    result_text.config(state="disabled")
    
    loading_canvas.pack(fill="both", expand=True)
    loading_animation.start()
    
    def generate_in_thread():
        generated = generate_recipe(prompt, model, tokenizer)
        app.after(0, lambda: display_result(generated))
    
    threading.Thread(target=generate_in_thread, daemon=True).start()

def display_result(result):
    loading_animation.stop()
    loading_canvas.pack_forget()
    
    # Add the result with fade-in effect
    result_text.config(state="normal")
    result_text.delete(1.0, "end")
    
    # Split result into sections (assuming format: Title, Ingredients, Instructions)
    sections = re.split(r'(ingredients:|instructions:)', result, flags=re.IGNORECASE)
    
    if len(sections) >= 3:
        # Title
        result_text.insert("end", sections[0].strip() + "\n\n", "title")
        
        # Ingredients
        result_text.insert("end", "INGREDIENTS:\n", "section_header")
        ingredients = sections[2].strip().split('\n')
        for ingredient in ingredients:
            if ingredient.strip():
                result_text.insert("end", "• " + ingredient.strip() + "\n", "ingredient")
        result_text.insert("end", "\n")
        
        # Instructions
        if len(sections) >= 5:
            result_text.insert("end", "INSTRUCTIONS:\n", "section_header")
            instructions = sections[4].strip().split('\n')
            for i, instruction in enumerate(instructions):
                if instruction.strip():
                    result_text.insert("end", f"{i+1}. {instruction.strip()}\n", "instruction")
    else:
        # If parsing fails, just show the raw text
        result_text.insert("end", result)
    
    result_text.config(state="disabled")
    
    # Show save button at the center and try another button below it
    button_frame.pack(side="bottom", pady=20)
    save_button.pack(side="top", pady=5)
    try_another_button.pack(side="top", pady=10)

# Utility function for widget fade-in animation
def fade_in_widget(widget, duration=10):
    alpha = 0
    
    def update_alpha():
        nonlocal alpha
        alpha += 0.1
        if alpha <= 1.0:
            # For custom widgets we can't change alpha directly
            # So we just make it visible at the end
            if alpha > 0.9:
                widget.lift()
            app.after(50, update_alpha)
    
    update_alpha()

# Function to save recipe
def save_recipe():
    recipe_text = result_text.get(1.0, "end-1c")
    if not recipe_text:
        return
        
    try:
        from datetime import datetime
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recipe_{now}.txt"
        
        with open(filename, "w") as f:
            f.write(recipe_text)
        
        messagebox.showinfo("Success", f"Recipe saved as {filename}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save recipe: {str(e)}")

# Function to clear for a new recipe
def try_another():
    prompt_entry.delete(0, "end")
    result_text.config(state="normal")
    result_text.delete(1.0, "end")
    result_text.config(state="disabled")
    button_frame.pack_forget()
    prompt_entry.focus_set()

# Title in header
header_frame = tb.Frame(app, style="HeaderFrame.TFrame")
header_frame.pack(fill="x", side="top")

title_label = tb.Label(header_frame, text="DishCrafter", style="Header.TLabel")
title_label.pack(pady=(20, 5))

subtitle_label = tb.Label(header_frame, text="Recipe Generator", style="SubHeader.TLabel")
subtitle_label.pack(pady=(0, 20))

# Main content area
content_frame = tb.Frame(app, style="TFrame")
content_frame.pack(fill="both", expand=True, padx=30, pady=30)

# Prompt Entry with label
prompt_frame = tb.Frame(content_frame, style="TFrame")
prompt_frame.pack(fill="x", pady=15)

prompt_label = tb.Label(prompt_frame, text="What would you like to cook?", 
                      font=("Helvetica", 14, "bold"))
prompt_label.pack(anchor="w", pady=(0, 10))

# FIXED RoundedEntry class that properly handles input
class RoundedEntry(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_COLOR)
        
        self.entry_var = tk.StringVar()
        self.font = kwargs.get("font", ("Helvetica", 12))
        
        # Create the canvas for the rounded background
        self.canvas = tk.Canvas(self, height=40, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(fill="x", expand=True)
        
        # Create the entry widget
        self.entry = tk.Entry(self, textvariable=self.entry_var, 
                           font=self.font, bd=0, bg=PRIMARY_COLOR,
                           fg=TEXT_COLOR, highlightthickness=0,
                           insertbackground=DARK_COLOR)
        
        # Place entry on top of canvas
        self.entry.place(in_=self.canvas, x=10, y=2, relwidth=0.95, height=36)
        
        # Draw rounded rectangle on canvas
        self.rounded_bg = create_rounded_rectangle(self.canvas, 2, 2, 
                                                int(self.canvas.winfo_reqwidth())-4, 38, 
                                                radius=19, fill=PRIMARY_COLOR, 
                                                outline=SECONDARY_COLOR, width=2)
        
        # Lower the background behind the entry
        self.canvas.tag_lower(self.rounded_bg)
        
        # Update canvas when frame resizes
        self.bind("<Configure>", self._on_resize)
    
    def _on_resize(self, event):
        # Update the rounded rectangle size when frame resizes
        width = event.width
        self.canvas.delete(self.rounded_bg)
        self.rounded_bg = create_rounded_rectangle(self.canvas, 2, 2, width-4, 38, 
                                                radius=19, fill=PRIMARY_COLOR, 
                                                outline=SECONDARY_COLOR, width=2)
        # Make sure entry resizes properly
        self.entry.place(in_=self.canvas, x=10, y=2, relwidth=0.95, height=36)
    
    def get(self):
        return self.entry_var.get()
    
    def delete(self, first, last):
        self.entry.delete(first, last)
    
    def insert(self, index, string):
        self.entry.insert(index, string)
    
    def focus_set(self):
        self.entry.focus_set()
    
    def bind(self, event, func):
        self.entry.bind(event, func)

# Create custom rounded entry
prompt_entry = RoundedEntry(prompt_frame, font=("Helvetica", 12))
prompt_entry.pack(fill="x", ipady=5)
prompt_entry.bind("<Return>", lambda e: on_generate())

# Generate Button - using custom rounded button
generate_button = RoundedButton(content_frame, width=200, height=50, 
                              bg_color=ACCENT_COLOR, text="Generate Recipe")
generate_button.config(command=on_generate)
generate_button.pack(pady=20)

# Loading canvas for animation
loading_canvas = tk.Canvas(content_frame, height=50, bg=BG_COLOR, 
                        highlightthickness=0)
loading_animation = LoadingAnimation(loading_canvas)

# Result area
result_frame = tb.Frame(content_frame, style="TFrame")
result_frame.pack(fill="both", expand=True, pady=10)

result_label = tb.Label(result_frame, text="Your Recipe:", font=("Helvetica", 14, "bold"))
result_label.pack(anchor="w", pady=(0, 10))

# Create custom rounded text frame
class RoundedText(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_COLOR, bd=0, highlightthickness=0)
        
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Text widget inside canvas
        self.text = tk.Text(self.canvas, **kwargs)
        self.text_window = self.canvas.create_window(10, 10, anchor="nw", window=self.text, 
                                                  width=self.winfo_reqwidth()-20, height=self.winfo_reqheight()-20)
        
        # Rounded rectangle background
        self.bg_rect = create_rounded_rectangle(self.canvas, 0, 0, self.winfo_reqwidth(), self.winfo_reqheight(), 
                                             radius=15, fill=PRIMARY_COLOR, outline=SECONDARY_COLOR, width=2)
        
        # Make sure text is on top
        self.canvas.tag_lower(self.bg_rect)
        
        # Update layout on resize
        self.bind("<Configure>", self._on_resize)
    
    def _on_resize(self, event):
        # Update rounded rectangle and text window
        width, height = event.width, event.height
        self.canvas.delete(self.bg_rect)
        self.bg_rect = create_rounded_rectangle(self.canvas, 0, 0, width, height, 
                                             radius=15, fill=PRIMARY_COLOR, outline=SECONDARY_COLOR, width=2)
        self.canvas.itemconfig(self.text_window, width=width-20, height=height-20)
    
    def config(self, **kwargs):
        self.text.config(**kwargs)
    
    def get(self, *args):
        return self.text.get(*args)
    
    def delete(self, *args):
        return self.text.delete(*args)
    
    def insert(self, *args):
        return self.text.insert(*args)
    
    def tag_configure(self, *args, **kwargs):
        return self.text.tag_configure(*args, **kwargs)

# Custom text widget with styling
result_text_frame = RoundedText(result_frame)
result_text_frame.pack(fill="both", expand=True, padx=5, pady=5)

result_text = result_text_frame.text
result_text.config(height=15, font=("Helvetica", 11), wrap="word", state="disabled", 
                bg=PRIMARY_COLOR, bd=0, relief="flat", padx=15, pady=15)

# Configure text tags for styling
result_text.tag_configure("title", font=("Helvetica", 14, "bold"), foreground=DARK_COLOR)
result_text.tag_configure("section_header", font=("Helvetica", 12, "bold"), foreground=ACCENT_COLOR)
result_text.tag_configure("ingredient", font=("Helvetica", 11))
result_text.tag_configure("instruction", font=("Helvetica", 11))

# Create button frame for consistent placement
button_frame = tb.Frame(content_frame, style="TFrame")

# Create buttons - Using darker colors for better visibility
save_button = RoundedButton(button_frame, width=200, height=40, 
                          bg_color=DARK_COLOR, text="Save Recipe")
save_button.config(command=save_recipe)

# Try another button with improved visibility
try_another_button = RoundedButton(button_frame, width=200, height=40, 
                                 bg_color=ACCENT_COLOR, text="Try Another Recipe")
try_another_button.config(command=try_another)

# Footer
footer_frame = tb.Frame(app, style="TFrame")
footer_frame.pack(fill="x", side="bottom", pady=10)

footer_text = tb.Label(footer_frame, text="© 2025 Gourmet AI | Professional Recipe Generator", 
                     font=("Helvetica", 8))
footer_text.pack()

# Focus the prompt entry initially
prompt_entry.focus_set()

# Animated tooltip system
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)
    
    def show(self, event=None):
        x, y = 0, 0
        if hasattr(self.widget, "winfo_x"):
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, 
                      background=DARK_COLOR, foreground="white",
                      relief="solid", borderwidth=1,
                      font=("Helvetica", 10, "normal"), padx=5, pady=2)
        label.pack()
        
        # Animate appearance
        self.tooltip.attributes("-alpha", 0.0)
        self.fade_in()
    
    def fade_in(self, alpha=0.0):
        if self.tooltip:
            alpha += 0.1
            if alpha <= 1.0:
                self.tooltip.attributes("-alpha", alpha)
                self.tooltip.after(30, lambda: self.fade_in(alpha))
    
    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

# Add tooltips to UI elements
ToolTip(generate_button, "Click to generate a recipe based on your input")
ToolTip(prompt_entry, "Enter ingredients, cuisine type, or dietary preferences")

# Add a welcome animation
def welcome_animation():
    # Create and place welcome overlay
    overlay = tk.Canvas(app, bg=DARK_COLOR, highlightthickness=0)
    overlay.place(x=0, y=0, relwidth=1, relheight=1)
    
    # Logo text
    logo_text = overlay.create_text(400, 300, text="DishCrafter", 
                                  fill="white", font=("Georgia", 36, "bold"))
    tagline = overlay.create_text(400, 350, text="Your Professional Recipe Assistant", 
                               fill="white", font=("Helvetica", 16))
    
    # Animate fade out
    for i in range(10, -1, -1):
        alpha = i/10
        overlay.configure(bg=f"#{int(int(DARK_COLOR[1:3], 16)*alpha):02x}"
                          f"{int(int(DARK_COLOR[3:5], 16)*alpha):02x}"
                          f"{int(int(DARK_COLOR[5:7], 16)*alpha):02x}")
        app.update()
        time.sleep(0.25)
    
    overlay.destroy()

# Run the welcome animation after a short delay
app.after(200, welcome_animation)

# Run the app
app.mainloop()