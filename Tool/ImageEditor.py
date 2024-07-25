import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageEnhance, ImageTk, ImageOps, UnidentifiedImageError
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import io
import base64
import cv2
from datetime import datetime

class ImageEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Editor")
        self.root.configure(bg="white")

        self.image_path = None
        self.original_image = None
        self.processed_image = None
        self.preview_image = None
        
        self.exposure_value = 1.0
        
        self.laplacian_value = 1.0

        self.selected_filter = None
        self.preview_mode = False
        self.apply_global = False

        self.history = []
        self.history_labels = []
        self.redo_history = []

        self.rect = None
        self.rect_id = None
        self.rect_start_x = None
        self.rect_start_y = None

        self.create_menu()
        self.create_widgets()
        self.create_filter_buttons()
        self.create_history_panel()

        self.root.bind('<Control-z>', lambda event: self.undo_last_action())
        self.root.bind('<Control-y>', lambda event: self.redo_last_action())
        self.root.bind('<Control-o>', lambda event: self.open_image())
        self.root.bind('<Control-s>', lambda event: self.save_image())
        self.root.bind('<Control-m>', lambda event: self.mirror_image())
        self.root.bind('<Control-h>', lambda event: self.show_histogram_window())
        self.root.bind('<Control-w>', lambda event: self.close_image())
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_menu(self):
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open", command=self.open_image, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_image, accelerator="Ctrl+S")
        file_menu.add_command(label="Close", command=self.close_image, accelerator="Ctrl+W")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        menu_bar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self.undo_last_action, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo_last_action, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Resize", command=self.resize_image)
        edit_menu.add_command(label="Rotate", command=self.rotate_image)
        edit_menu.add_command(label="Mirror Image", command=self.mirror_image, accelerator="Ctrl+M")
        menu_bar.add_cascade(label="Edit", menu=edit_menu)

        report_menu = tk.Menu(menu_bar, tearoff=0)
        report_menu.add_command(label="Generate Report", command=self.generate_report)
        menu_bar.add_cascade(label="Report", menu=report_menu)

        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Zoom", command=self.zoom_options)
        view_menu.add_command(label="Histogram", command=self.show_histogram_window, accelerator="Ctrl+H")
        menu_bar.add_cascade(label="View", menu=view_menu)
        
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Shortcut", command=self.show_shortcut_dialog)
        help_menu.add_command(label="Help", command=self.show_help_dialog)
        help_menu.add_command(label="About", command=self.show_about_dialog)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu_bar)

    def create_widgets(self):
        self.editor_frame = tk.Frame(self.root)

        self.canvas = tk.Canvas(self.editor_frame, bg="gray")
        self.canvas.pack(expand=True, fill=tk.BOTH)

        self.exposure_slider = tk.Scale(self.root, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, label="Exposure", command=self.adjust_exposure)
        self.exposure_slider.bind("<ButtonRelease-1>", self.update_exposure)
        self.exposure_slider.set(1.0)
        self.exposure_slider.pack(pady=10)
        self.exposure_slider.pack_forget()
        
        self.laplacian_slider = tk.Scale(self.root, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, label="Laplacian Intensity", command=self.adjust_laplacian_intensity)
        self.laplacian_slider.bind("<ButtonRelease-1>", self.apply_laplacian_contrast)
        self.laplacian_slider.set(1)
        self.laplacian_slider.pack(pady=10)
        self.laplacian_slider.pack_forget()

        self.editor_frame.pack(expand=True, fill=tk.BOTH)

        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        
    def create_history_panel(self):
        history_panel = tk.Frame(self.root, bg="gray", width=200)
        history_panel.pack(side=tk.BOTTOM, fill=tk.Y)

        tk.Label(history_panel, text="Cronologia:", bg="gray").pack(pady=10)

        self.history_text = tk.Text(history_panel, height=10, wrap=tk.WORD, bg="white")
        self.history_text.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
                    
    def create_filter_buttons(self):
        filter_frame = tk.Frame(self.root, bg="white")
        filter_frame.pack(side=tk.TOP, pady=10)

        self.filter_var = tk.StringVar()
        
        self.exposure_icon = ImageTk.PhotoImage(Image.open("icons/exposure_icon.png"))
        self.equalize_icon = ImageTk.PhotoImage(Image.open("icons/equalize_icon.png"))
        self.laplacian_icon = ImageTk.PhotoImage(Image.open("icons/laplacian_icon.png"))

        exposure_button = tk.Radiobutton(filter_frame, image=self.exposure_icon, text="Exposure", variable=self.filter_var, value="exposure", indicatoron=False, command=self.select_filter)
        exposure_button.pack(side=tk.LEFT, padx=5)

        laplacian_button = tk.Radiobutton(filter_frame, image=self.laplacian_icon, text="Laplacian", variable=self.filter_var, value="laplacian", indicatoron=False, command=self.select_filter)
        laplacian_button.pack(side=tk.LEFT, padx=5)

        self.area_var = tk.StringVar()
        
        histogram_button = tk.Radiobutton(filter_frame, image=self.equalize_icon, text="Equalizzazione Istogramma", variable=self.filter_var, value="equalize", indicatoron=False, command=self.equalize_histogram)
        histogram_button.pack(side=tk.LEFT, padx=5)

        global_button = tk.Radiobutton(filter_frame, text="Globale", variable=self.area_var, value="global", indicatoron=False, command=self.select_area)
        global_button.pack(side=tk.LEFT, padx=5)

        local_button = tk.Radiobutton(filter_frame, text="Locale", variable=self.area_var, value="local", indicatoron=False, command=self.select_area)
        local_button.pack(side=tk.LEFT, padx=5)
        
    def open_image(self):
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"),
            ("All files", "*.*")  # Opzione per mostrare tutti i file
        ]
        file_path = filedialog.askopenfilename(filetypes=filetypes)

        if file_path:
            try:
                self.original_image = Image.open(file_path)
                self.processed_image = self.original_image.copy()
                self.display_image(self.processed_image)
                self.history = []  # Resetta la cronologia quando apri una nuova immagine
                self.update_history(f"Opened image: {file_path}\n")
            except (FileNotFoundError, PIL.UnidentifiedImageError):
                messagebox.showerror("Errore", "Impossibile aprire il file. Assicurati che sia un'immagine valida.")     
                
    def save_image(self):
            if not self.processed_image:
                messagebox.showwarning("Warning", "No image to save.")
                return

            # Finestra di dialogo per il salvataggio con checkbox
            save_dialog = tk.Toplevel(self.root)
            save_dialog.title("Save Image")

            # Checkbox per la generazione del report
            self.generate_report_var = tk.BooleanVar(value=False)  # Variabile per la checkbox
            report_checkbox = tk.Checkbutton(save_dialog, text="Generate Report", variable=self.generate_report_var)
            report_checkbox.pack(pady=10)

            # Pulsante Salva
            save_button = tk.Button(save_dialog, text="Save", command=lambda: self.save_image_with_report(save_dialog))
            save_button.pack(pady=5)

    def save_image_with_report(self, save_dialog):
        self.image_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"),
                       ("JPEG files", "*.jpg"),
                       ("All files", "*.*")])

        if self.image_path:
            self.processed_image.save(self.image_path)
            self.update_history(f"Saved image to: {self.image_path}\n")

            # Genera il report se la checkbox è selezionata
            if self.generate_report_var.get():
                self.generate_report()

        save_dialog.destroy()
            
    def close_image(self):
        if self.processed_image:
            save_changes = messagebox.askyesnocancel("Save Changes", "Do you want to save changes before closing?")
            if save_changes is True:
                self.save_image()  # Salva l'immagine se l'utente sceglie "Sì"
            elif save_changes is None:  # L'utente ha scelto "Cancel"
                return  # Non chiudere l'immagine

            # Chiudi l'immagine e reimposta i dati
            self.canvas.delete("all")
            self.image_path = None
            self.original_image = None
            self.processed_image = None
            self.preview_image = None
            self.history = []
            self.redo_history = []
            self.update_history_display()
            
    def on_closing(self):
        if messagebox.askokcancel("Quit", "Are you sure you want to quit?"):
            self.root.destroy()

    def on_mouse_press(self, event):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None

        self.rect_start_x = event.x
        self.rect_start_y = event.y

        self.rect_id = self.canvas.create_rectangle(
            self.rect_start_x, self.rect_start_y,
            self.rect_start_x, self.rect_start_y,
            outline="red", width=2)

    def on_mouse_drag(self, event):
        self.canvas.coords(self.rect_id, self.rect_start_x, self.rect_start_y, event.x, event.y)

    def on_mouse_release(self, event):
        if self.rect_id:
            coords = self.canvas.coords(self.rect_id)
            if len(coords) == 4:
                x0, y0, x1, y1 = map(int, coords)
                if x0 != x1 and y0 != y1:
                    self.rect = (x0, y0, x1, y1)
                    print(f"Rettangolo rilasciato: ({x0}, {y0}, {x1}, {y1})")
                    if self.selected_filter:
                        self.preview_filter()
                else:
                    print("L'area di selezione ha dimensioni zero.")

    def resize_image(self):
        if not self.original_image:
            messagebox.showwarning("Warning", "No image loaded.")
            return

        width = simpledialog.askinteger("Input", "Enter new width:")
        height = simpledialog.askinteger("Input", "Enter new height:")

        if width and height:
            self.processed_image = self.processed_image.resize((width, height), Image.LANCZOS)
            self.original_image = self.processed_image.copy()
            self.display_image(self.original_image)
            self.update_history(f"Resized image to: {width}x{height}\n")
            
    def on_resize(self, event):
        if self.original_image:
            self.display_image(self.processed_image)

    def rotate_image(self):
        if not self.original_image:
            messagebox.showwarning("Warning", "No image loaded.")
            return

        angle = simpledialog.askinteger("Input", "Enter rotation angle:")
        if angle:
            self.processed_image = self.processed_image.rotate(angle, expand=True)
            self.original_image = self.processed_image.copy()
            self.display_image(self.original_image)
            self.update_history(f"Rotated image by: {angle} degrees\n")

    def mirror_image(self):
        if not self.original_image:
            messagebox.showwarning("Warning", "No image loaded.")
            return

        self.processed_image = ImageOps.mirror(self.processed_image)
        self.original_image = self.processed_image.copy()
        self.display_image(self.original_image)
        self.update_history("Mirrored image\n")
        
    def select_filter(self):
        self.selected_filter = self.filter_var.get()

        self.exposure_slider.pack_forget()
        self.laplacian_slider.pack_forget()

        if self.selected_filter == "exposure":
            self.exposure_slider.pack(pady=10)
            
        elif self.selected_filter == "laplacian":
            self.laplacian_slider.pack(pady=10)
            
    def select_area(self):
        self.apply_global = self.area_var.get() == "global"
        
    def display_image(self, image):
        self.preview_image = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_image)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        
    def adjust_exposure(self, value):
        self.exposure_value = float(value)
        self.preview_filter()
        
    def update_exposure(self, event):
        self.exposure_value = float(self.exposure_slider.get())
        self.apply_filter_to_current_image()
        self.update_history(f"Adjusted exposure to: {self.exposure_value}\n")
        
    def adjust_laplacian_intensity(self, value):
        self.laplacian_value = float(value)
        self.preview_filter()
        
    def apply_laplacian_contrast(self, event):
        if not self.processed_image:
            return

    def apply_laplacian(image):
        # Conversione in scala di grigi
        gray_image = image.convert("L")

        # Applicazione del filtro Laplaciano con intensità regolabile
        laplacian_array = np.array(gray_image, dtype=np.float32)
        laplacian_array = cv2.Laplacian(laplacian_array, cv2.CV_32F, ksize=3, scale=self.laplacian_value)
        laplacian_array = np.clip(laplacian_array, 0, 255)
        laplacian_image = Image.fromarray(np.uint8(laplacian_array))

        # Se l'immagine originale è a colori, unisci l'immagine Laplaciana con l'originale
        if image.mode == "RGB":
            return Image.merge("RGB", (laplacian_image, laplacian_image, laplacian_image))
        else:
            return laplacian_image

    if self.apply_global:
        self.processed_image = apply_laplacian(self.processed_image)
    elif self.rect:
        x0, y0, x1, y1 = self.rect
        crop = self.processed_image.crop((x0, y0, x1, y1))
        enhanced_crop = apply_laplacian(crop)
        self.processed_image.paste(enhanced_crop, (x0, y0, x1, y1))

    self.display_image(self.processed_image)
        
    def apply_filter_to_current_image(self):
        if self.processed_image:
            if self.selected_filter == "exposure":
                self.apply_exposure()
            elif self.selected_filter == "laplacian":
                self.apply_laplacian_contrast()
            self.display_image(self.processed_image)
        
    def preview_filter(self):
        if not self.original_image:
            return

        image = self.original_image.copy()

        if self.selected_filter:
            if self.selected_filter == "exposure":
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(self.exposure_value)
                
            elif self.selected_filter == "laplacian":
                # Conversione in scala di grigi
                gray_image = image.convert("L")

                # Applicazione del filtro Laplaciano con intensità regolabile
                laplacian_array = np.array(gray_image, dtype=np.float32)
                laplacian_array = cv2.Laplacian(laplacian_array, cv2.CV_32F, ksize=3, scale=self.laplacian_value)
                laplacian_array = np.clip(laplacian_array, 0, 255)
                laplacian_image = Image.fromarray(np.uint8(laplacian_array))

                # Unisci l'immagine Laplaciana con l'originale per aumentare i dettagli
                image = Image.merge("RGB", (laplacian_image, laplacian_image, laplacian_image))

            if self.apply_global:
                self.processed_image = image
            elif self.rect:
                x0, y0, x1, y1 = self.rect
                cropped = image.crop((x0, y0, x1, y1))
                self.processed_image.paste(cropped, (x0, y0))

        self.display_image(self.processed_image)
        
    def equalize_histogram(self):
        if self.original_image:
            # Converti l'immagine in scala di grigi se è a colori
            if self.original_image.mode != "L":
                img_gray = self.original_image.convert("L")
            else:
                img_gray = self.original_image.copy()

            # Equalizza l'istogramma dell'immagine in scala di grigi
            img_eq = ImageOps.equalize(img_gray)

            # Se l'immagine originale era a colori, converti l'immagine equalizzata nello stesso spazio colore
            if self.original_image.mode != "L":
                self.processed_image = Image.merge(
                    self.original_image.mode,
                    [img_eq] + [channel for channel in self.original_image.split()[1:]]
                )
            else:
                self.processed_image = img_eq

            self.update_history("Histogram Equalization\n")
            self.original_image = self.processed_image.copy()
            self.display_image(self.original_image)
            
    def update_history(self, action):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.history.append({
            'Date': timestamp,
            'action': action,
            'image': self.processed_image.copy(),
            'exposure_value': self.exposure_value,
            'laplacian_value': self.laplacian_value,
            'selected_filter': self.selected_filter,
            'apply_global': self.apply_global,
            'rect': self.rect
        })
        self.history_labels.append(action)
        self.redo_history = []
        self.update_history_display()

        if self.history:
            self.history_text.delete("end-2c", tk.END)  
            self.history_text.delete("1.0", tk.END)
            
            for entry in self.history:
                self.history_text.insert(tk.END, entry['action'])
        else:
            self.history_text.delete("1.0", tk.END) 
            
    def undo_last_action(self):
        if self.history:
            if self.history[-1]['action'].startswith("Opened image"):
                messagebox.showinfo("Info", "Cannot undo 'Opened Image' action.")
                return
        
            last_action = self.history.pop()
            self.redo_history.append(last_action)
            self.history_labels.pop()

            if self.history:
                last_state = self.history[-1]
                self.processed_image = last_state['image'].copy()
                self.exposure_value = last_state['exposure_value']
                self.laplacian_value = last_state['laplacian_value']
                self.selected_filter = last_state['selected_filter']
                self.apply_global = last_state['apply_global']
                self.rect = last_state['rect']

                # Aggiorna i controlli dell'interfaccia utente
                self.exposure_slider.set(self.exposure_value)
                self.laplacian_slider.set(self.laplacian_value)
                self.filter_var.set(self.selected_filter)
                self.area_var.set("global" if self.apply_global else "local")
            else:
                self.processed_image = self.original_image.copy()
                self.reset_filters()

            self.display_image(self.processed_image)
            self.update_history_display()
        else:
            messagebox.showinfo("Info", "No actions to undo.")

    def reset_filters(self):
        self.exposure_value = 1.0
        self.laplacian_value = 1.0
        self.selected_filter = None
        self.apply_global = False
        self.rect = None
        self.exposure_slider.set(1.0)
        self.laplacian_slider.set(1.0)
        self.filter_var.set('')
        self.area_var.set('')

    def redo_last_action(self):
        if self.redo_history:
            last_action = self.redo_history.pop()
            self.history.append(last_action)
            self.history_labels.append(last_action['action'])  # Aggiungi l'etichetta dell'azione ripristinata
            self.processed_image = last_action['image']
            self.display_image(self.processed_image)
            self.update_history_display()
        else:
            messagebox.showinfo("Info", "No actions to redo.")
            
    def show_histogram_window(self):
        if not self.original_image:
            messagebox.showerror("Errore", "Nessuna immagine aperta.")
            return

        histogram_window = tk.Toplevel(self.root)
        histogram_window.title("Histogram")
        histogram_window.geometry("800x600")

        # Create the figure and axis for the histogram
        fig, ax = plt.subplots()
        canvas = FigureCanvasTkAgg(fig, master=histogram_window)
        canvas.get_tk_widget().pack()

        def update_histogram(channel):
            ax.clear()
            if channel == 'RGB':
                colors = ('r', 'g', 'b')
                for idx, color in enumerate(colors):
                    hist = self.original_image.histogram()[idx * 256:(idx + 1) * 256]
                    ax.plot(hist, color=color)
            else:
                channel_index = {'R': 0, 'G': 1, 'B': 2}[channel]
                hist = self.original_image.histogram()[channel_index * 256:(channel_index + 1) * 256]
                ax.plot(hist, color=channel.lower())
            canvas.draw()

        channel_var = tk.StringVar(value='RGB')
        channel_selector = ttk.Combobox(histogram_window, textvariable=channel_var, values=['RGB', 'R', 'G', 'B'])
        channel_selector.pack()

        exposure_scale = tk.Scale(histogram_window, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, label="Exposure")
        exposure_scale.set(1.0)

        def apply_exposure(event):
            if self.apply_global:
                enhancer = ImageEnhance.Brightness(self.processed_image)
                self.processed_image = enhancer.enhance(self.exposure_value)
            elif self.rect:
                x0, y0, x1, y1 = self.rect
                crop = self.processed_image.crop((x0, y0, x1, y1))
                enhancer = ImageEnhance.Brightness(crop)
                enhanced_crop = enhancer.enhance(self.exposure_value)
                self.processed_image.paste(enhanced_crop, (x0, y0, x1, y1))

        def finalize_exposure(event):
            self.exposure_value = exposure_scale.get()
            channel = channel_var.get()
            self.original_image = self.adjust_exposure_histogram(self.original_image, self.exposure_value, channel)
            self.display_image(self.original_image)
            self.update_history(f"Adjusted {channel} exposure to {self.exposure_value}\n")

        exposure_scale.bind("<B1-Motion>", apply_exposure)
        exposure_scale.bind("<ButtonRelease-1>", finalize_exposure)
        exposure_scale.pack()

        channel_selector.bind("<<ComboboxSelected>>", lambda event: update_histogram(channel_var.get()))
        update_histogram('RGB')

    def adjust_exposure_histogram(self, image, value, channel):
        channels = image.split()
        if len(channels) == 4:
            r, g, b, a = channels
        else:
            r, g, b = channels
            a = None

        if channel == 'R':
            r = ImageEnhance.Brightness(r).enhance(value)
        elif channel == 'G':
            g = ImageEnhance.Brightness(g).enhance(value)
        elif channel == 'B':
            b = ImageEnhance.Brightness(b).enhance(value)
        elif channel == 'RGB':
            r = ImageEnhance.Brightness(r).enhance(value)
            g = ImageEnhance.Brightness(g).enhance(value)
            b = ImageEnhance.Brightness(b).enhance(value)

        if a:
            return Image.merge("RGBA", (r, g, b, a))
        else:
            return Image.merge("RGB", (r, g, b))
                
    def generate_report(self):
        report_file_path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML files", "*.html")])
        if report_file_path:
            with open(report_file_path, 'w') as file:
                file.write("<html><body>")
                file.write("<h1>Image Edit Report</h1>")
                file.write("<ul>")
                for idx, entry in enumerate(self.history):
                    buffer = io.BytesIO()
                    entry['image'].save(buffer, format="PNG")  # Salva l'immagine direttamente dal dizionario
                    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    file.write(f"<li>{entry['action']} - {entry['Date']}</li>")
                    file.write(f'<img src="data:image/png;base64,{img_str}" alt="Step {idx+1}" style="max-width: 100%; height: auto;">')
                file.write("</ul>")
                file.write("</body></html>")
            messagebox.showinfo("Report Saved", f"Report saved to {report_file_path}")
            
    def zoom_options(self):
        if not self.processed_image:
            messagebox.showwarning("Warning", "No image to zoom.")
            return

        zoom_window = tk.Toplevel(self.root)
        zoom_window.title("Zoom Options")
        zoom_window.geometry("300x200")

        tk.Label(zoom_window, text="Zoom Level:", font=("Helvetica", 12)).pack(pady=10)
        zoom_slider = tk.Scale(zoom_window, from_=1, to=10, resolution=0.1, orient=tk.HORIZONTAL)
        zoom_slider.set(1.0)
        zoom_slider.pack(pady=20)
        zoom_slider.bind("<ButtonRelease-1>", lambda event: self.zoom_image(zoom_slider.get()))

    def zoom_image(self, zoom_level):
        if not self.original_image:
            messagebox.showwarning("Warning", "No image to zoom.")
            return

        width, height = self.original_image.size
        new_size = (int(width * zoom_level), int(height * zoom_level))
        self.processed_image = self.original_image.resize(new_size)
        self.original_image = self.original_image.resize(new_size)
        self.display_image(self.original_image)
        self.update_history(f"Zoomed image to {zoom_level}x\n")
        
    def show_help_dialog(self):
        help_text = "Help:\n"
        help_text += "Exposure Filter:\n"
        help_text += "1) Click Exposure Button\n"
        help_text += "2) Select Global or Local, if you do not choose anything, you can drag the mouse directly on the canvas and the filter will be applied locally.\n"
        help_text += "3) if You chosen Local Area Drag to select an area on the image.\n"
        help_text += "4) Use the Exposure slider to adjust the exposure value.\n"
        help_text += "\n"
        help_text += "Laplacian Filter:\n"
        help_text += "1) Click Laplacian Button\n"
        help_text += "2) Select Global or Local, if you do not choose anything, you can drag the mouse directly on the canvas and the filter will be applied locally.\n"
        help_text += "3) if You chosen Local Area Drag to select an area on the image.\n"
        help_text += "4) Use the Exposure slider to adjust Filter value.\n"
        help_text += "\n"
        help_text += "Equalize Histogram:\n"
        help_text += "1) Click Equalize Histogram Button\n"
        help_text += "2) The histogram of the image will be equalized.\n"

        messagebox.showinfo("Help", help_text)
        
    def show_about_dialog(self):
        about_text = "About\n"
        about_text += "Image Editor\n"
        about_text += "Version 1.0\n"
        about_text += "Author: Mirko Morana\n"

        messagebox.showinfo("About", about_text)
        
    def show_shortcut_dialog(self):
        shortcut_text = "Shortcuts:\n"
        shortcut_text += "Ctrl+O: Open Image\n"
        shortcut_text += "Ctrl+S: Save Image\n"
        shortcut_text += "Ctrl+W: Close Image\n"
        shortcut_text += "Ctrl+Z: Undo\n"
        shortcut_text += "Ctrl+Y: Redo\n"
        shortcut_text += "Ctrl+M: Mirror Image\n"
        shortcut_text += "Ctrl+H: Show Histogram\n"

        messagebox.showinfo("Shortcuts", shortcut_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageEditor(root)
    root.mainloop()