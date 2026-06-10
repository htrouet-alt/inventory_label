from pathlib import Path
import socket
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
from csv import writer

CONFIG_FILE = Path("config.conf")
LOG_FILE = Path("log.csv")
ZPL_FOLDER = Path("zpl")
DEFAULT_PRINTER_PORT = 9100

# --- UI layout constants ---
UI_WINDOW_SIZE = "420x260"
UI_RESIZABLE = False
UI_LABEL_FONT = ("Arial", 12)
UI_INPUT_FONT = ("Arial", 12)
UI_SMALL_FONT = ("Arial", 10)
UI_STATUS_FONT = ("Arial", 10, "bold")
UI_BUTTON_FONT = ("Arial", 10)
UI_ENTRY_WIDTH = 30
UI_COMBO_WIDTH = UI_ENTRY_WIDTH
UI_PAD_Y_SMALL = 5
UI_PAD_Y_MEDIUM = 20
UI_PAD_X_SMALL = 5
UI_PAD_X_MEDIUM = 10
UI_LAYOUT: dict[str, int] = {
    "template_label_top": 5,
    "template_combo_top": 5,
    "serial_label_top": 5,
    "serial_entry_top": 5,
    "status_frame_top": 5,
    "button_frame_top": 20,
}


def load_config(path: Path = CONFIG_FILE) -> dict:
    config = {
        "url": "",
        "log": True,
        "prnt_ip": "",
        "prnt_port": DEFAULT_PRINTER_PORT,
    }

    if not path.is_file():
        return config

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = [part.strip() for part in line.split("=", 1)]
        if value.startswith(("'", '"')) and value.endswith(("'", '"')):
            value = value[1:-1]

        key = key.lower()
        if key == "url":
            config["url"] = value
        elif key == "log":
            config["log"] = value.lower() in ("1", "true", "yes", "on")
        elif key == "prnt_ip":
            config["prnt_ip"] = value
        elif key == "prnt_port":
            try:
                config["prnt_port"] = int(value)
            except ValueError:
                pass

    return config


def join_url(base_url: str, serial: str) -> str:
    if not base_url:
        return serial
    return base_url.rstrip("/") + "/" + serial


def list_zpl_templates(folder: Path = ZPL_FOLDER) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(
        [item.name for item in folder.iterdir() if item.is_file() and item.suffix.lower() == ".zpl"]
    )


def list_csv_files(folder: Path = Path(".")) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(
        [item.name for item in folder.iterdir() if item.is_file() and item.suffix.lower() == ".csv"]
    )


def send_to_printer(printer_ip, printer_port, payload):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(10)
        sock.connect((printer_ip, printer_port))
        sock.sendall(payload.encode("utf-8"))


def check_printer_available(printer_ip, printer_port):
    if not printer_ip or not printer_port:
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            sock.connect((printer_ip, printer_port))
        return True
    except OSError:
        return False


def ensure_log_file(path: Path = LOG_FILE) -> None:
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as log_file:
        writer(log_file).writerow(["Barcode", "Date", "Time"])


class QCLabelTool:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Inventar Label Tool")
        self.root.geometry(UI_WINDOW_SIZE)
        self.root.resizable(UI_RESIZABLE, UI_RESIZABLE)

        self.config = load_config()
        self.zpl_files = list_zpl_templates()
        self.csv_files = list_csv_files()
        self.log_reader_window = None

        self.create_widgets()
        self.update_printer_status()
        ensure_log_file()

    def create_widgets(self) -> None:
        device_label = tk.Label(self.root, text="Label template:", font=UI_LABEL_FONT)
        device_label.pack(pady=UI_LAYOUT["template_label_top"])

        default_template = self.zpl_files[0] if self.zpl_files else ""
        self.device_var = tk.StringVar(value=default_template)

        device_frame = tk.Frame(self.root)
        device_frame.pack(pady=UI_LAYOUT["template_combo_top"])

        self.device_combo = ttk.Combobox(
            device_frame,
            textvariable=self.device_var,
            values=self.zpl_files,
            state="readonly",
            font=UI_INPUT_FONT,
            width=UI_COMBO_WIDTH,
        )
        self.device_combo.pack()

        label = tk.Label(self.root, text="Serial Number:", font=UI_LABEL_FONT)
        label.pack(pady=UI_LAYOUT["serial_label_top"])

        self.serial_entry = tk.Entry(self.root, font=UI_INPUT_FONT, width=UI_ENTRY_WIDTH)
        self.serial_entry.pack(pady=UI_LAYOUT["serial_entry_top"])
        self.serial_entry.focus()
        self.serial_entry.bind("<Return>", lambda event: self.print_label())

        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=UI_LAYOUT["status_frame_top"])

        status_label = tk.Label(status_frame, text="Printer status:", font=UI_SMALL_FONT)
        status_label.pack(side=tk.LEFT)

        self.printer_status_label = tk.Label(
            status_frame,
            text="Checking...",
            font=UI_STATUS_FONT,
        )
        self.printer_status_label.pack(side=tk.LEFT, padx=UI_PAD_X_SMALL)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=UI_LAYOUT["button_frame_top"])

        self.print_button = tk.Button(
            button_frame,
            text="Print",
            command=self.print_label,
            width=10,
            font=UI_BUTTON_FONT,
        )
        self.print_button.pack(side=tk.LEFT, padx=UI_PAD_X_MEDIUM)

        self.open_log_button = tk.Button(
            button_frame,
            text="Open Log",
            command=self.open_log_reader,
            width=10,
            font=UI_BUTTON_FONT,
        )
        self.open_log_button.pack(side=tk.LEFT, padx=UI_PAD_X_MEDIUM)

        self.close_button = tk.Button(
            button_frame,
            text="Close",
            command=self.close_app,
            width=10,
            font=UI_BUTTON_FONT,
        )
        self.close_button.pack(side=tk.LEFT, padx=UI_PAD_X_MEDIUM)
    
    def update_printer_status(self):
        printer_ip = self.config.get('prnt_ip')
        printer_port = self.config.get('prnt_port')
        if not printer_ip:
            self.printer_status_label.config(text="No printer IP", fg="red")
            return
        if not printer_port:
            self.printer_status_label.config(text="No printer port", fg="red")
            return
        available = check_printer_available(printer_ip, printer_port)
        if available:
            self.printer_status_label.config(text=f"Available ({printer_ip}:{printer_port})", fg="green")
        else:
            self.printer_status_label.config(text=f"Unavailable ({printer_ip}:{printer_port})", fg="red")

    def open_log_reader(self) -> None:
        if self.log_reader_window and tk.Toplevel.winfo_exists(self.log_reader_window):
            self.log_reader_window.lift()
            return

        self.log_reader_window = tk.Toplevel(self.root)
        self.log_reader_window.title("Log Reader")
        self.log_reader_window.geometry("800x450")
        self.log_reader_window.resizable(True, True)

        top_frame = tk.Frame(self.log_reader_window)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        file_label = tk.Label(top_frame, text="Select CSV file:", font=UI_LABEL_FONT)
        file_label.pack(side=tk.LEFT)

        self.log_file_var = tk.StringVar()
        self.csv_files = list_csv_files()
        self.log_file_combo = ttk.Combobox(
            top_frame,
            textvariable=self.log_file_var,
            values=self.csv_files,
            state="readonly",
            font=UI_INPUT_FONT,
            width=40,
        )
        self.log_file_combo.pack(side=tk.LEFT, padx=UI_PAD_X_MEDIUM)
        self.log_file_combo.bind("<<ComboboxSelected>>", lambda event: self.load_csv_file(self.log_file_var.get()))

        table_frame = tk.Frame(self.log_reader_window)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.log_tree = ttk.Treeview(table_frame, show="headings")
        self.log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_tree.bind("<ButtonRelease-1>", self.on_log_table_click)

        self.log_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.log_tree.configure(yscrollcommand=self.log_scrollbar.set)

        actions_frame = tk.Frame(self.log_reader_window)
        actions_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.selected_cell_var = tk.StringVar(value="Selected cell: none")
        self.selected_cell_label = tk.Label(actions_frame, textvariable=self.selected_cell_var, font=UI_SMALL_FONT)
        self.selected_cell_label.pack(side=tk.LEFT)

        copy_line_button = tk.Button(
            actions_frame,
            text="Copy Line",
            command=self.copy_selected_line,
            width=12,
            font=UI_BUTTON_FONT,
        )
        copy_line_button.pack(side=tk.RIGHT, padx=UI_PAD_X_MEDIUM)

        copy_field_button = tk.Button(
            actions_frame,
            text="Copy Field",
            command=self.copy_selected_field,
            width=12,
            font=UI_BUTTON_FONT,
        )
        copy_field_button.pack(side=tk.RIGHT)

        close_reader_button = tk.Button(
            actions_frame,
            text="Close",
            command=self.log_reader_window.destroy,
            width=12,
            font=UI_BUTTON_FONT,
        )
        close_reader_button.pack(side=tk.RIGHT, padx=UI_PAD_X_MEDIUM)

        if self.csv_files:
            self.log_file_var.set(self.csv_files[0])
            self.load_csv_file(self.csv_files[0])
        else:
            messagebox.showinfo("Info", "No CSV files found in the application directory.")

    def load_csv_file(self, file_name: str) -> None:
        csv_path = Path(file_name)
        if not csv_path.is_file():
            messagebox.showerror("Error", f"CSV file not found: {file_name}")
            return

        for child in self.log_tree.get_children():
            self.log_tree.delete(child)
        self.log_tree.config(columns=())

        with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
            rows = list(self._read_csv_rows(csv_file))

        if not rows:
            return

        headers = rows[0]
        self.log_tree.config(columns=[f"col{i}" for i in range(len(headers))])
        for idx, header in enumerate(headers):
            self.log_tree.heading(f"col{idx}", text=header)
            self.log_tree.column(f"col{idx}", width=150, anchor=tk.W)

        for row in rows[1:]:
            values = [value for value in row]
            self.log_tree.insert("", tk.END, values=values)

        self.selected_row = None
        self.selected_column = None
        self.selected_cell_var.set("Selected cell: none")

    def _read_csv_rows(self, csv_file):
        from csv import reader as csv_reader

        for row in csv_reader(csv_file):
            yield row

    def on_log_table_click(self, event) -> None:
        item_id = self.log_tree.identify_row(event.y)
        column_id = self.log_tree.identify_column(event.x)
        if not item_id or not column_id:
            return

        self.selected_row = item_id
        self.selected_column = column_id
        col_index = int(column_id.replace("#", "")) - 1
        values = self.log_tree.item(item_id, "values")
        if 0 <= col_index < len(values):
            selected_value = values[col_index]
            self.selected_cell_var.set(f"Selected cell: {selected_value}")
        else:
            self.selected_cell_var.set("Selected cell: none")

    def copy_selected_line(self) -> None:
        if not getattr(self, "selected_row", None):
            messagebox.showwarning("Warning", "Select a row first")
            return

        values = self.log_tree.item(self.selected_row, "values")
        if not values:
            return

        from io import StringIO
        from csv import writer as csv_writer

        buffer = StringIO()
        csv_writer(buffer, lineterminator="").writerow(values)
        text = buffer.getvalue()

        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Copied", "Selected line copied to clipboard")

    def copy_selected_field(self) -> None:
        if not getattr(self, "selected_row", None) or not getattr(self, "selected_column", None):
            messagebox.showwarning("Warning", "Select a field first")
            return

        col_index = int(self.selected_column.replace("#", "")) - 1
        values = self.log_tree.item(self.selected_row, "values")
        if 0 <= col_index < len(values):
            text = values[col_index]
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("Copied", "Selected field copied to clipboard")
        else:
            messagebox.showwarning("Warning", "Invalid field selection")

    def print_label(self) -> None:
        barcode = self.serial_entry.get().strip()

        if not barcode:
            messagebox.showwarning("Warning", "Please enter a serial number")
            return

        if not self.zpl_files:
            messagebox.showerror(
                "Configuration Error",
                "Keine ZPL-Templates im zpl-Ordner gefunden.",
            )
            return

        selected_template = self.device_var.get()
        if not selected_template:
            messagebox.showerror(
                "Configuration Error",
                "Bitte wählen Sie eine ZPL-Vorlage aus der Liste aus.",
            )
            return

        base_url = self.config.get("url")
        if not base_url:
            messagebox.showerror(
                "Configuration Error",
                "Basis-URL in config.conf nicht lesbar.\n"
                "Bitte url = 'https://baseurls_example.de/verzeichnis/' hinzufügen.",
            )
            return

        full_url = join_url(base_url, barcode)

        try:
            now = datetime.now()
            timestamp = now.strftime("%H:%M:%S")
            date_string = now.strftime("%d/%m/%Y")

            if self.config.get("log", True):
                with LOG_FILE.open("a", newline="", encoding="utf-8") as log_file:
                    writer(log_file).writerow([barcode, date_string, timestamp])

            zpl_path = ZPL_FOLDER / selected_template
            with zpl_path.open("r", encoding="utf-8") as zpl_file:
                zpl_template = zpl_file.read()

            zpl_payload = zpl_template.replace("{PLACEHOLDER_URL}", full_url)
            zpl_payload = zpl_payload.replace("{PLACEHOLDER_SERIAL}", barcode)

            printer_ip = self.config.get("prnt_ip")
            printer_port = self.config.get("prnt_port")
            if not printer_ip:
                messagebox.showerror(
                    "Configuration Error",
                    "Drucker-IP ist nicht in config.conf konfiguriert (prnt_ip).",
                )
                return

            if not printer_port:
                messagebox.showerror(
                    "Configuration Error",
                    "Drucker-Port ist nicht in config.conf konfiguriert (prnt_port).",
                )
                return

            send_to_printer(printer_ip, printer_port, zpl_payload)
            self.update_printer_status()
            self.serial_entry.delete(0, tk.END)
            self.serial_entry.focus()

        except Exception as ex:
            messagebox.showerror("Error", f"Druckfehler: {ex}")
    
    def close_app(self):
        self.root.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = QCLabelTool(root)
    root.mainloop()
    