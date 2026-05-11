import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import subprocess

# ═══════════════════════════════════════════════════════════════════
#  TOOLTIP CLASS
# ═══════════════════════════════════════════════════════════════════

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        # Calculate position to show tooltip
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify="left",
                         background="#ffffe0", relief="solid", borderwidth=1,
                         font=("tahoma", "8", "normal"), padx=5, pady=2)
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

# ═══════════════════════════════════════════════════════════════════
#  TOOLTIP DEFINITIONS
# ═══════════════════════════════════════════════════════════════════

TOOLTIPS = {
    "paths": {
        "input_folder": "The directory containing the PDF drawings you want to analyze.",
        "output_folder": "The directory where the analyzed PDFs will be saved."
    },
    "targets": "A list of subjects (Authors/Subjects in PDF) that represent the pencil lines to be processed.",
    "search": {
        "search_rect_margin": "Expands the search area around your pencil mark (in points) to find nearby PDF lines.",
        "wall_max_dist": "Maximum distance allowed from your pencil mark to a PDF line for it to be considered a 'wall'.",
        "min_wall_dist": "The 'Dead Zone': Ignores any CAD lines closer than this distance to your pencil mark to avoid picking up your own drawing.",
        "min_seg_len": "Ignores short PDF segments (noise) smaller than this length during the initial wall search."
    },
    "graph": {
        "graph_snap_dist": "Grid size for snapping PDF line endpoints together. Larger values bridge bigger gaps between lines.",
        "snap_tolerance": "Final step: Snaps the boundary polygon vertices to the closest PDF lines within this distance."
    },
    "walk": {
        "max_steps": "Maximum number of connected line segments the algorithm will follow for a single wall.",
        "min_coverage": "The percentage (0.0 to 1.0) of the pencil mark's length that must be matched by PDF lines to be valid.",
        "par_tolerance_deg": "Angle tolerance (degrees) for matching parallel lines during the graph walk.",
        "perp_tolerance_deg": "Angle tolerance (degrees) for detecting corners and perpendicular turns.",
        "deviation_margin": "Restricts the walk to a bounding box around your pencil mark expanded by this distance.",
        "only_straight": "If checked, the algorithm will not follow turns or corners and will stay strictly within the length of your pencil mark.",
        "sampling_interval": "The distance (in points) between probe points along the stroke when using straight-line mode. Smaller values are more thorough but slower."
    },
    "debug": {
        "show_walk_dots": "If checked, draws small dots in the output PDF to show exactly which lines the algorithm followed.",
        "dot_radius": "Size of the debug dots drawn in the output PDF.",
        "left_dot_color": "RGB color (0.0 to 1.0) for the left-side wall debug dots.",
        "right_dot_color": "RGB color (0.0 to 1.0) for the right-side wall debug dots."
    },
    "label": {
        "font_size": "Font size for the numeric ID label placed at the center of the detected boundary.",
        "text_color": "RGB color (0.0 to 1.0) for the ID label text.",
        "fill_color": "RGB color (0.0 to 1.0) for the background box behind the ID label."
    },
    "grill_detection": {
        "tolerance": "Distance tolerance (in points) for matching line endpoints. Lower is stricter.",
        "threshold": "Minimum percentage of lines (0.0-1.0) that must match. 0.8 = 80%.",
        "grid_size": "Spatial grid size for faster searching. Recommended 10-20.",
        "tag_font_size": "Font size for the numeric tags placed on detected grills.",
        "tag_text_color": "RGB color (0.0 to 1.0) for the tag numbers.",
        "tag_fill_color": "RGB color (0.0 to 1.0) for the tag background box."
    }
}

class ConfigEditor:
    def __init__(self, root, config_path="config.json"):
        self.root = root
        self.root.title("Project Configuration Editor")
        self.config_path = config_path
        self.config = {}
        self.vars = {}

        self.load_config()
        self.setup_ui()

    def load_config(self):
        try:
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")
            self.root.destroy()

    def save_config(self, show_alert=True):
        new_config = self.get_config_from_vars(self.config, self.vars)
        try:
            with open(self.config_path, "w") as f:
                json.dump(new_config, f, indent=4)
            if show_alert:
                messagebox.showinfo("Success", "Configuration saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")

    def get_config_from_vars(self, template, vars_dict):
        result = {}
        for key, value in template.items():
            if isinstance(value, dict):
                result[key] = self.get_config_from_vars(value, vars_dict[key])
            elif key == "targets":
                result[key] = [t.strip() for t in vars_dict[key].get().split(",") if t.strip()]
            elif isinstance(value, list):
                result[key] = []
                for i, v in enumerate(vars_dict[key]):
                    orig_type = type(template[key][i])
                    val = v.get()
                    result[key].append(orig_type(val) if orig_type in (int, float) else val)
            else:
                orig_type = type(value)
                val = vars_dict[key].get()
                if orig_type in (int, float, bool):
                    if orig_type is int:
                        result[key] = int(round(float(val)))
                    else:
                        result[key] = orig_type(val)
                else:
                    result[key] = val
        return result

    def setup_ui(self):
        # Create Notebook for Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.vars = {}
        
        # General/Paths Tab
        paths_tab = self.add_tab("General")
        self.vars["paths"] = self.create_path_widgets(paths_tab, self.config["paths"], "paths")
        
        targets_frame = tk.LabelFrame(paths_tab, text="Detection Targets", padx=10, pady=5)
        targets_frame.pack(fill="x", padx=10, pady=5)
        v = tk.StringVar(value=", ".join(self.config["targets"]))
        self.vars["targets"] = v
        entry = tk.Entry(targets_frame, textvariable=v)
        entry.pack(fill="x")
        ToolTip(entry, TOOLTIPS["targets"])

        # Boundary Detector Tab
        boundary_tab = self.add_tab("Boundary Detector")
        for key in ["search", "graph", "walk", "debug", "label"]:
            frame = tk.LabelFrame(boundary_tab, text=key.capitalize(), padx=10, pady=5)
            frame.pack(fill="x", padx=10, pady=5)
            self.vars[key] = self.create_sub_widgets(frame, self.config[key], key)

        # Grill Detection Tab
        grill_tab = self.add_tab("Grill Detection")
        frame = tk.LabelFrame(grill_tab, text="Matching Parameters", padx=10, pady=5)
        frame.pack(fill="x", padx=10, pady=5)
        self.vars["grill_detection"] = self.create_sub_widgets(frame, self.config["grill_detection"], "grill_detection")

        # Bottom Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", pady=10)

        tk.Button(btn_frame, text="Save Config", command=lambda: self.save_config(True), bg="#4CAF50", fg="white", padx=10).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Run Boundary Detector", command=lambda: self.run_script("boundary_detector.py"), bg="#2196F3", fg="white", padx=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Run Grill Detector", command=lambda: self.run_script("detect_grills.py"), bg="#FF9800", fg="white", padx=10).pack(side="left", padx=5)

    def add_tab(self, title):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text=title)
        
        # Add Canvas and Scrollbar to Tab
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        return scrollable_frame

    def create_sub_widgets(self, parent, data, category):
        vars_dict = {}
        for key, value in data.items():
            row = tk.Frame(parent)
            row.pack(fill="x", pady=2)
            lbl = tk.Label(row, text=key, width=20, anchor="w")
            lbl.pack(side="left")
            
            if category in TOOLTIPS and key in TOOLTIPS[category]:
                ToolTip(lbl, TOOLTIPS[category][key])

            if isinstance(value, bool):
                v = tk.BooleanVar(value=value)
                vars_dict[key] = v
                tk.Checkbutton(row, variable=v).pack(side="left")
            
            elif isinstance(value, (int, float)):
                v = tk.DoubleVar(value=value)
                vars_dict[key] = v
                
                min_val, max_val = 0, 1000
                if "coverage" in key or "threshold" in key: min_val, max_val = 0.0, 1.0
                elif "tolerance" in key and "deg" in key: min_val, max_val = 0, 180
                elif "tolerance" in key: min_val, max_val = 0, 50
                elif "radius" in key: min_val, max_val = 1, 20
                elif "size" in key: min_val, max_val = 5, 50
                elif "steps" in key: min_val, max_val = 10, 500

                entry = tk.Entry(row, textvariable=v, width=10)
                entry.pack(side="right", padx=5)
                
                scale = tk.Scale(row, from_=min_val, to=max_val, variable=v, 
                                 orient="horizontal", showvalue=0, resolution=0.01 if isinstance(value, float) else 1)
                scale.pack(side="right", fill="x", expand=True)

            elif isinstance(value, list):
                vars_dict[key] = []
                for i, component in enumerate(value):
                    cv = tk.DoubleVar(value=component)
                    vars_dict[key].append(cv)
                    tk.Scale(row, from_=0, to=1, variable=cv, orient="horizontal", 
                             showvalue=0, resolution=0.01, width=10).pack(side="left", fill="x", expand=True)
                    tk.Entry(row, textvariable=cv, width=5).pack(side="left", padx=2)

        return vars_dict

    def create_path_widgets(self, parent, data, category):
        vars_dict = {}
        for key, value in data.items():
            row = tk.Frame(parent)
            row.pack(fill="x", pady=2)
            lbl = tk.Label(row, text=key, width=15, anchor="w")
            lbl.pack(side="left")

            if category in TOOLTIPS and key in TOOLTIPS[category]:
                ToolTip(lbl, TOOLTIPS[category][key])
            
            v = tk.StringVar(value=value)
            vars_dict[key] = v
            tk.Entry(row, textvariable=v).pack(side="left", fill="x", expand=True, padx=5)
            tk.Button(row, text="Browse", command=lambda var=v: self.browse_folder(var)).pack(side="right")
        return vars_dict

    def browse_folder(self, var):
        folder = filedialog.askdirectory()
        if folder:
            var.set(os.path.normpath(folder))

    def run_script(self, script_name):
        self.save_config(show_alert=False)
        try:
            subprocess.Popen(["start", "cmd", "/K", f"python {script_name}"], shell=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run {script_name}: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("700x850")
    app = ConfigEditor(root)
    root.mainloop()
