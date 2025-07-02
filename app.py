# app.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import threading
import time
import traceback
from utils import load_config, fetch_xml_feed, parse_xml_feed, merge_dataframes, load_csv_data

class ProductManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GastroPro Product Manager")
        self.geometry("600x400")
        self.main_df = None
        self.categories = []
        self.config = load_config()
        self.processing = False

        if not self.config:
            # If config could not be loaded, the application will not start
            self.destroy()
            return
        
        self.create_widgets()
        self.center_window()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self):
        """Centers the application window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
    def create_widgets(self):
        """Creates and arranges GUI components."""
        # Frame for CSV upload
        upload_frame = ttk.LabelFrame(self, text="1. Nahrať CSV súbor", padding="15")
        upload_frame.pack(pady=10, padx=20, fill="x")

        self.upload_label = ttk.Label(upload_frame, text="Nebol nahraný žiadny súbor.")
        self.upload_label.pack(side="left", padx=(0, 10))

        upload_button = ttk.Button(upload_frame, text="Vybrať CSV", command=self.load_csv_file)
        upload_button.pack(side="right")

        # Frame pre výber kategórií
        self.filter_frame = ttk.LabelFrame(self, text="2. Filtrovať produkty podľa kategórií", padding="15")
        self.filter_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.filter_frame.grid_columnconfigure(0, weight=1)
        self.filter_frame.grid_columnconfigure(1, weight=1)

        filter_label = ttk.Label(self.filter_frame, text="Vyberte kategórie na export:")
        filter_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Checkbox for "Select all"
        self.select_all_var = tk.BooleanVar()
        self.select_all_var.trace_add('write', self.toggle_all_categories)
        self.select_all_checkbox = ttk.Checkbutton(self.filter_frame, text="Vybrať všetky kategórie", variable=self.select_all_var)
        self.select_all_checkbox.grid(row=1, column=0, columnspan=2, sticky="w")

        self.category_frame = ttk.Frame(self.filter_frame)
        self.category_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.category_frame.grid_rowconfigure(0, weight=1)
        self.category_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.category_frame, borderwidth=0, background="#ffffff")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar = ttk.Scrollbar(self.category_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.inner_frame = ttk.Frame(self.canvas, padding="5")
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        
        self.inner_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        # Frame for export button
        export_frame = ttk.Frame(self, padding="15")
        export_frame.pack(pady=10, padx=20, fill="x")

        self.generate_button = ttk.Button(export_frame, text="Generovať a Exportovať CSV", command=self.generate_and_export_csv, state=tk.DISABLED)
        self.generate_button.pack(fill="x")

        # Initially hide filter and export button
        self.filter_frame.pack_forget()
        self.generate_button.pack_forget()

    def on_frame_configure(self, event):
        """Adjusts the scroll region for canvas."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """Adjusts the width of the inner frame."""
        # Canvas window ID is different from winfo_children
        # We need to access the window ID created with create_window
        self.canvas.itemconfig(1, width=event.width)

    def load_csv_file(self):
        """Loads the CSV file and displays categories."""
        file_path = filedialog.askopenfilename(
            title="Vyberte CSV súbor",
            filetypes=[("CSV files", "*.csv")]
        )
        if not file_path:
            return

        try:
            # Call load_csv_data with the file path
            self.main_df = load_csv_data(file_path)
            
            if self.main_df.empty:
                # If no data was loaded, there was probably an error
                self.main_df = None
                self.upload_label.config(text="Zatiaľ nebol nahratý žiadny súbor.")
                self.filter_frame.pack_forget()
                self.generate_button.pack_forget()
                return

            self.upload_label.config(text=f"Nahraný súbor: {file_path.split('/')[-1]}")
            
            # Get unique categories
            if 'Hlavna kategória' in self.main_df.columns:
                self.categories = sorted(self.main_df['Hlavna kategória'].dropna().unique().tolist())
                self.populate_category_checkboxes()
                self.filter_frame.pack(pady=10, padx=20, fill="both", expand=True)
                self.generate_button.pack(fill="x")
                self.generate_button.config(state=tk.NORMAL)
            else:
                messagebox.showwarning("Chýbajúci stĺpec", "V CSV súbore nebol nájdený stĺpec 'Hlavna kategória'. Filtrovanie nie je možné.")
                self.main_df = None
                self.upload_label.config(text="Zatiaľ nebol nahratý žiadny súbor.")
                self.filter_frame.pack_forget()
                self.generate_button.pack_forget()

        except Exception as e: # Catches any other errors
            messagebox.showerror("Chyba načítania", f"Nepodarilo sa načítať CSV súbor.\nChyba: {e}")
            self.main_df = None
            self.upload_label.config(text="Zatiaľ nebol nahratý žiadny súbor.")
            self.filter_frame.pack_forget()
            self.generate_button.pack_forget()
            
    def populate_category_checkboxes(self):
        """Fills the GUI with checkboxes for categories."""
        # Clear existing checkboxes
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        
        self.category_vars = {}
        for category in self.categories:
            var = tk.BooleanVar(value=True) # All categories selected by default
            self.category_vars[category] = var
            chk = ttk.Checkbutton(self.inner_frame, text=category, variable=var)
            chk.pack(anchor="w")

        # Update scroll region
        self.inner_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.select_all_var.set(True) # Set "select all" to true after loading

    def toggle_all_categories(self, *args):
        """Selects/deselects all categories."""
        if not hasattr(self, 'category_vars'):
            return
        
        state = self.select_all_var.get()
        for var in self.category_vars.values():
            var.set(state)

    def generate_and_export_csv(self):
        """Starts the entire CSV generation process using a background thread."""
        if self.main_df is None:
            messagebox.showwarning("Chýbajúce dáta", "Najprv nahrajte hlavný CSV súbor.")
            return

        selected_categories = [
            cat for cat, var in self.category_vars.items() if var.get()
        ]

        if not selected_categories:
            messagebox.showwarning("Bez výberu", "Vyberte aspoň jednu kategóriu na export.")
            return
            
        # Disable the generate button to prevent multiple clicks
        self.generate_button.config(state=tk.DISABLED)
        
        # Show loading cursor
        self.configure(cursor="wait")
        self.update()
        
        # Show processing indicator in the UI instead of toast
        self.processing = True
        print("Started background processing...")
        
        # Create a processing thread
        processing_thread = threading.Thread(
            target=self._process_data_in_background, 
            args=(selected_categories,)
        )
        processing_thread.daemon = True  # Thread will exit when main app exits
        processing_thread.start()
    
    def _process_data_in_background(self, selected_categories):
        """Process data in a background thread to keep UI responsive."""
        try:
            # 1. Filter the main CSV
            filtered_df = self.main_df[self.main_df['Hlavna kategória'].isin(selected_categories)].copy() 
            
            if filtered_df.empty:
                # Use after to safely interact with UI from the thread
                self.after(0, lambda: messagebox.showwarning("Prázdny výsledok", "Žiadne produkty nespĺňajú vybrané kritériá."))
                self.after(0, lambda: self._reset_ui_state())
                return
            
            # 2. Download and parse XML feeds
            print(f"Starting to fetch {len(self.config['xml_feeds'])} XML feeds...")
            feed_dataframes = []
            for feed_name, feed_info in self.config['xml_feeds'].items():
                print(f"Fetching feed: {feed_name} from {feed_info['url']}")
                try:
                    root = fetch_xml_feed(feed_info['url'])
                    if root is None:
                        print(f"Error: Feed {feed_name} returned None")
                        continue
                        
                    print(f"Successfully fetched feed {feed_name}, parsing XML...")
                    # Pass root_element_tag and feed_name to parse_xml_feed for specialized processing
                    df = parse_xml_feed(root, feed_info['root_element'], feed_info['mapping'], feed_name)
                    
                    if df is None or df.empty:
                        print(f"Warning: Empty DataFrame from feed {feed_name}")
                    else:
                        print(f"Successfully parsed feed {feed_name} - got {len(df)} rows and {len(df.columns)} columns")
                        print(f"Sample columns: {list(df.columns)[:5]}")
                        
                    feed_dataframes.append(df)
                except Exception as e:
                    print(f"Error processing feed {feed_name}: {e}")
                    print(traceback.format_exc())

            # 3. Merge data
            print(f"Starting merge with {len(feed_dataframes)} feed DataFrames")
            print(f"Main DataFrame has {len(filtered_df)} rows and {len(filtered_df.columns)} columns")
            for i, feed_df in enumerate(feed_dataframes):
                if feed_df is not None and not feed_df.empty:
                    print(f"Feed {i+1} has {len(feed_df)} rows and {len(feed_df.columns)} columns")
                else:
                    print(f"Feed {i+1} is empty or None")
                    
            final_df = merge_dataframes(filtered_df, feed_dataframes, self.config['final_csv_columns'])
            print(f"Merge complete. Final DataFrame has {len(final_df)} rows and {len(final_df.columns)} columns")
            
            # Show toast and save dialog from the main thread
            self.after(0, lambda: self._show_merge_success_and_save_dialog(final_df))
            
        except Exception as e:
            # Use after to safely show error message from the thread
            self.after(0, lambda: messagebox.showerror("Chyba generovania", f"Pri generovaní došlo k chybe:\n{e}"))
            self.after(0, lambda: self._reset_ui_state())
    
    def _show_merge_success_and_save_dialog(self, final_df):
        """Show success message and then the save dialog from the main thread."""
        try:
            print("Merge was successful, preparing to show save dialog")
            
            # Open save dialog directly
            self._open_save_dialog(final_df)
        except Exception as e:
            print(f"Error in _show_merge_success_and_save_dialog: {e}")
            print(traceback.format_exc())
            messagebox.showerror("Chyba pri ukladaní", f"Chyba pri príprave dialógu:\n{e}")
            self._reset_ui_state()
    
    def _open_save_dialog(self, final_df):
        """Open the save dialog and handle file saving."""
        try:
            print("Opening save dialog...")
            save_path = filedialog.asksaveasfilename(
                initialfile="Merged.csv",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Uložiť výsledný CSV súbor"
            )
            
            print(f"Save path selected: {save_path if save_path else 'None - user canceled'}")
            
            if save_path:
                print("Saving file...")
                final_df.to_csv(save_path, index=False, encoding='utf-8-sig')  # Use utf-8-sig for BOM
                print("File saved successfully")
                messagebox.showinfo("Great success!", f"Súbor bol úspešne uložený do: {save_path}")
        except Exception as e:
            print(f"Error in _open_save_dialog: {e}")
            print(traceback.format_exc())
            messagebox.showerror("Chyba pri ukladaní", f"Pri ukladaní súboru došlo k chybe:\n{e}")
        finally:
            print("Resetting UI state")
            self._reset_ui_state()
    
    def _reset_ui_state(self):
        """Reset the UI state after processing completes."""
        print("UI state reset")
        self.processing = False
        self.configure(cursor="")
        self.generate_button.config(state=tk.NORMAL)

    def on_closing(self):
        """Handles the window closing event."""
        if messagebox.askokcancel("Ukončiť", "Naozaj chcete aplikáciu ukončiť?"):
            self.destroy()

if __name__ == "__main__":
    app = ProductManager()
    if app.winfo_exists(): # Checks if the window was created
        app.mainloop()