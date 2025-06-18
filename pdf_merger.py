import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
from PyPDF2 import PdfMerger
from pdf2image import convert_from_path
import threading

POPPLER_PATH = r"C:\\poppler\\poppler-24.08.0\\Library\\bin"

class FileMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Merger (PDF + Images)")
        self.root.geometry("1000x600")

        contact = tk.Label(root, text="Contact: https://afzalbadshah.com/index.php/afzal-badshah/", fg="blue", cursor="hand2")
        contact.pack()
        contact.bind("<Button-1>", lambda e: os.system('start https://afzalbadshah.com/index.php/afzal-badshah/'))

        self.files = []
        self.selected_index = None

        #tk.Label(root, text="🔹 Drag PDF/Images below. Select a file and reorder using buttons. ❌ to delete.").pack()

        self.canvas = tk.Canvas(root, bg="white")
        self.scrollbar = tk.Scrollbar(root, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(fill="x", side="bottom")
        self.canvas.pack(expand=True, fill="both")

        self.scrollable_frame = tk.Frame(self.canvas, bg="white")
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind("<<Drop>>", self.drop_file)
        self.scrollable_frame.drop_target_register(DND_FILES)
        self.scrollable_frame.dnd_bind("<<Drop>>", self.drop_file)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="⬆️ Move Up", command=self.move_up).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="⬇️ Move Down", command=self.move_down).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="📁 Merge Files to PDF", command=self.merge_files).pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(root, mode='determinate')
        self.progress.pack(fill='x', padx=10, pady=(0, 5))

        self.root.bind("<Configure>", lambda e: self.refresh_thumbnails())

    def drop_file(self, event):
        paths = self.root.tk.splitlist(event.data)
        for raw_path in paths:
            path = raw_path.strip('{}')
            ext = os.path.splitext(path)[1].lower()
            if ext in ('.pdf', '.png', '.jpg', '.jpeg') and os.path.exists(path):
                if path not in [f["path"] for f in self.files]:
                    try:
                        thumb = self.get_thumbnail(path)
                        self.add_thumbnail(path, thumb)
                    except Exception as e:
                        messagebox.showerror("Error", f"Cannot load file:\n{e}")

    def get_thumbnail(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            img = convert_from_path(path, first_page=1, last_page=1, size=(100, 130), poppler_path=POPPLER_PATH)[0]
        else:
            img = Image.open(path)
            img.thumbnail((100, 130))
        return ImageTk.PhotoImage(img)

    def add_thumbnail(self, path, thumb):
        frame_index = len(self.files)
        frame = tk.Frame(self.scrollable_frame, bd=2, relief="groove", bg="white")
        label = tk.Label(frame, image=thumb, bg="white")
        label.image = thumb
        label.pack()
        size = os.path.getsize(path) // 1024
        name_label = tk.Label(frame, text=f"{os.path.basename(path)}\n({size} KB)", bg="white", wraplength=90)
        name_label.pack()

        del_btn = tk.Button(frame, text="❌", command=lambda i=frame_index: self.remove_file(i))
        del_btn.pack()

        frame.bind("<Button-1>", lambda e, i=frame_index: self.select_file(i))
        for child in frame.winfo_children():
            child.bind("<Button-1>", lambda e, i=frame_index: self.select_file(i))

        self.files.append({"path": path, "thumb": thumb, "widget": frame})
        self.refresh_thumbnails()

    def select_file(self, index):
        self.selected_index = index
        for i, file in enumerate(self.files):
            file["widget"].config(bg="lightblue" if i == index else "white")

    def move_up(self):
        idx = self.selected_index
        if idx is None or idx == 0: return
        self.files[idx], self.files[idx - 1] = self.files[idx - 1], self.files[idx]
        self.selected_index -= 1
        self.refresh_thumbnails()

    def move_down(self):
        idx = self.selected_index
        if idx is None or idx >= len(self.files) - 1: return
        self.files[idx], self.files[idx + 1] = self.files[idx + 1], self.files[idx]
        self.selected_index += 1
        self.refresh_thumbnails()

    def remove_file(self, index):
        self.files[index]["widget"].destroy()
        del self.files[index]
        self.selected_index = None
        self.refresh_thumbnails()

    def refresh_thumbnails(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.grid_forget()

        if self.canvas.winfo_width() <= 1:
            return

        columns = max(1, self.canvas.winfo_width() // 160)
        for i, file in enumerate(self.files):
            file["widget"].grid(row=i // columns, column=i % columns, padx=5, pady=5)
            file["widget"].config(bg="lightblue" if i == self.selected_index else "white")
            for b in file["widget"].winfo_children():
                if isinstance(b, tk.Button):
                    b.configure(command=lambda i=i: self.remove_file(i))

    def merge_files(self):
        if not self.files:
            messagebox.showerror("Error", "No files selected.")
            return

        out_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if not out_path:
            return

        def _merge():
            merger = PdfMerger()
            self.progress["maximum"] = len(self.files)
            self.progress["value"] = 0

            for i, f in enumerate(self.files):
                try:
                    merger.append(f["path"])
                except:
                    img = convert_from_path(f["path"], poppler_path=POPPLER_PATH)[0]
                    temp_img_path = f["path"] + ".png"
                    img.save(temp_img_path)
                    merger.append(temp_img_path)
                    os.remove(temp_img_path)

                self.progress["value"] = i + 1
                self.progress.update()

            merger.write(out_path)
            merger.close()
            self.progress["value"] = 0
            messagebox.showinfo("Success", f"Merged PDF saved to:\n{out_path}")

        threading.Thread(target=_merge).start()

# Run
if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = FileMergerApp(root)
    root.mainloop()
