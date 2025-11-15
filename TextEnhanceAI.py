import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
import difflib
import re
from datetime import datetime
import os
import threading

try:
    from ollama import Client
    try:
        # Prefer top-level list API when available
        from ollama import list as ollama_list, ListResponse
    except Exception:
        ollama_list = None
        ListResponse = None
except ImportError:
    print("Please install the ollama package (pip install ollama).")
    Client = None
    ollama_list = None
    ListResponse = None

# --------------
# Configurable prompts for each button
# --------------
PROMPTS = {
    "Grammar": "Fix grammar issues without altering the meaning.",
    "Proofread": "Proofread the text comprehensively, correcting errors and improving readability.",
    "Natural": "Refine awkward phrasing to make the text feel natural while preserving the original meaning.",
    "Streamline": "Remove unnecessary elements, clarify the message, and ensure coherence and ease of understanding.",
    "Awkward": "Fix only awkward or poorly written sentences without making other changes.",
    "Rewrite": "Rewrite the text to improve clarity, flow, and overall readability.",
    "Concise": "Make the text more concise by removing redundancy and unnecessary content.",
    "Polish": "Refine awkward words or phrases to give the text a polished and professional tone.",
    "Improve": "Enhance the text by proofreading and improving its clarity, flow, and coherence.",
}

# --------------
# Custom prompt helper (avoid private tkinter APIs)
# --------------
def ask_custom_string(title, prompt, parent=None):
    """Ask for a string using the standard dialog."""
    return simpledialog.askstring(title, prompt, parent=parent)


# --------------
# Simple Tooltip class
# --------------
class ToolTip:
    """
    A simple tooltip for tkinter widgets.
    Usage: create_tooltip(widget, text='Hello!')
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.x = self.y = 0

        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.showtip()

    def leave(self, event=None):
        self.hidetip()

    def showtip(self):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() - 45
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # removes the window decorations
        tw.geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("tahoma", "8", "normal")
        )
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


def create_tooltip(widget, text):
    """Helper to attach a tooltip with given text to a widget."""
    ToolTip(widget, text)


# --------------
# Main application class
# --------------
class EditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TextEnhanceAI Editor with Local LLM - V 0.12")

        # ----------------------
        # 1) Set starting size and use it as the minimum
        # ----------------------
        self.root.geometry("800x600")
        self.root.minsize(800, 600)

        # 2) Initialize widgets and buttons

        # Ollama client (make sure you've installed and are running your local LLM server)
        self.ollama_client = Client() if Client else None
        self.model_name = os.getenv("TEAI_MODEL", "llama3.1:8b")

        # Top bar: model selection
        top_bar = tk.Frame(self.root)
        top_bar.pack(fill=tk.X, padx=5, pady=5)
        model_label = tk.Label(top_bar, text="Model:")
        model_label.pack(side=tk.LEFT, padx=(0, 2))
        self.model_var = tk.StringVar(value=self.model_name)
        self.model_optionmenu = tk.OptionMenu(top_bar, self.model_var, self.model_name)
        self.model_optionmenu.pack(side=tk.LEFT, padx=(0, 6))
        refresh_btn = tk.Button(top_bar, text="Refresh", command=self.populate_model_menu)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 8))
        # Load models initially
        self.populate_model_menu()

        # Text area (scrolled)
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=80, height=25)
        self.text_area.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Frame for buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        self.btn_frame = btn_frame

        # Create standard editing buttons
        for label in ["Grammar", "Proofread", "Natural", "Streamline",
                      "Awkward", "Rewrite", "Concise", "Polish", "Improve"]:
            b = tk.Button(
                btn_frame, 
                text=label, 
                command=lambda lbl=label: self.run_llm_edit(lbl)
            )
            b.pack(side=tk.LEFT, padx=2)
            # Show the prompt in a tooltip
            create_tooltip(b, PROMPTS[label])

        # Add the Translate button BEFORE the "Custom" button
        translate_btn = tk.Button(btn_frame, text="Translate", command=self.run_translate_prompt)
        translate_btn.pack(side=tk.LEFT, padx=2)
        create_tooltip(translate_btn, "Prompt user for a target language and translate the text.")

        # Button for custom prompt
        custom_btn = tk.Button(btn_frame, text="Custom", command=self.run_custom_prompt)
        custom_btn.pack(side=tk.LEFT, padx=2)
        create_tooltip(custom_btn, "Enter your own custom instruction.")

        # Quit button
        tk.Button(
            btn_frame, text="Quit", command=self.root.quit
        ).pack(side=tk.RIGHT, padx=2)

        # Frame for apply-changes options
        self.accept_reject_frame = tk.Frame(self.root)
        self.accept_reject_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 3) Make the Accept/Reject button text colored
        tk.Button(
            self.accept_reject_frame,
            text="Accept All Changes",
            command=self.accept_all_changes,
            fg='green'
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            self.accept_reject_frame,
            text="Reject All Changes",
            command=self.reject_all_changes,
            fg='red'
        ).pack(side=tk.LEFT, padx=2)
        
        # We store the â€œdiff-annotatedâ€ version of the text in a separate place
        # so we can choose to accept or reject changes piecewise.
        self.diff_text = ""
        self.temp_html = ""  # If you want to store a temporary HTML version

        # For scratchpad logging:
        self.scratchpad_filename = None
        self.first_change_time = None

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, anchor="w")
        self.status_label.pack(fill=tk.X, padx=5, pady=(0,5))

    # --------------
    # Button callbacks
    # --------------
    def run_llm_edit(self, prompt_label):
        """Send the current text + editing prompt to the LLM and display the changes inline."""
        if not self.ollama_client:
            messagebox.showerror("Error", "Ollama client not initialized or not installed.")
            return

        user_text = self.text_area.get("1.0", tk.END).strip()
        if not user_text:
            messagebox.showinfo("Info", "Please enter text to edit.")
            return

        prompt_text = PROMPTS[prompt_label]
        self.start_llm_task(user_text, prompt_text)

    def run_custom_prompt(self):
        """Prompt user for a custom instruction, then run it."""
        if not self.ollama_client:
            messagebox.showerror("Error", "Ollama client not initialized or not installed.")
            return

        user_text = self.text_area.get("1.0", tk.END).strip()
        if not user_text:
            messagebox.showinfo("Info", "Please enter text to edit.")
            return

        # Custom prompt entry (80 chars wide)
        custom_prompt = ask_custom_string("Custom Prompt", "Enter your prompt:", parent=self.root)
        if custom_prompt:
            self.start_llm_task(user_text, custom_prompt)

    def run_translate_prompt(self):
        """
        Prompt the user for the language, then translate the text to that language.
        """
        if not self.ollama_client:
            messagebox.showerror("Error", "Ollama client not initialized or not installed.")
            return

        user_text = self.text_area.get("1.0", tk.END).strip()
        if not user_text:
            messagebox.showinfo("Info", "Please enter text to translate.")
            return

        # Ask user what language they want
        language = simpledialog.askstring("Translate", "Enter the target language:", parent=self.root)
        if language:
            # Construct a translation instruction
            translate_prompt = f"Translate the text into {language}. Return only the translated text."
            self.start_llm_task(user_text, translate_prompt)

    # --------------
    # LLM + diff logic
    # --------------
    def query_llm_and_show_diff(self, user_text, instruction):
        """Backwards-compatible: start async LLM work and update UI when done."""
        self.start_llm_task(user_text, instruction)

    def start_llm_task(self, user_text, instruction):
        """Start the LLM call in a background thread and update UI when done."""
        if not self.ollama_client:
            messagebox.showerror("Error", "Ollama client not initialized or not installed.")
            return

        def worker():
            system_prompt = (
                "You are a helpful, concise assistant that carefully edits text "
                "based on instructions. Return only the edited text, without extra commentary."
            )
            history = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Instruction:\n{instruction}\n\nText:\n{user_text}"}
            ]

            try:
                try:
                    selected_model = (self.model_var.get() or "").strip()
                except Exception:
                    selected_model = ""
                if not selected_model:
                    selected_model = self.model_name
                response = self.ollama_client.chat(
                    model=selected_model,
                    messages=history,
                    options={
                        'num_predict': 2048,
                        'temperature': 0.7,
                        'top_p': 0.9,
                    },
                )
                if "message" in response and "content" in response["message"]:
                    edited_text = response["message"]["content"].strip()
                else:
                    raise RuntimeError("No content received from LLM.")
            except Exception as e:
                self.root.after(0, lambda: (self.set_busy(False), messagebox.showerror("LLM Error", str(e))))
                return

            self.root.after(0, lambda: self._on_llm_result(user_text, instruction, edited_text))

        self.set_busy(True)
        self.status_var.set("Processing with LLMâ€¦")
        self.status_var.set("Processing with LLM...")
        threading.Thread(target=worker, daemon=True).start()

    def _on_llm_result(self, user_text, instruction, edited_text):
        # If it's the first time we are modifying text, create the scratchpad
        if not self.first_change_time:
            self.first_change_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.scratchpad_filename = f"TextEnhanceAI-scratchpad_{self.first_change_time}.md"

        # Show inline diff to the text widget
        self.show_inline_diff(user_text, edited_text)

        # Log to scratchpad with bold for differences
        bold_user_text, bold_edited_text = self.generate_bold_diff(user_text, edited_text)
        self.log_to_scratchpad(
            f"#Instruction: {instruction} #\n\n"
            f"##User Text:##\n{bold_user_text}\n\n"
            f"##Edited Text:##\n{bold_edited_text}\n\n"
        )
        self.status_var.set("Ready")
        self.set_busy(False)

    def set_busy(self, busy: bool):
        """Enable/disable buttons while background work runs."""
        state = tk.DISABLED if busy else tk.NORMAL
        # Top button row
        try:
            for w in self.btn_frame.winfo_children():
                if isinstance(w, tk.Button):
                    w.config(state=state)
        except Exception:
            pass
        # Accept/Reject row
        for w in self.accept_reject_frame.winfo_children():
            if isinstance(w, tk.Button):
                try:
                    w.config(state=state)
                except Exception:
                    pass

    def get_available_models(self):
        """Return a list of available local Ollama model names."""
        models = []
        # 1) Try official top-level API first
        if ollama_list is not None:
            try:
                resp = ollama_list()
                # Newer package: ListResponse with .models attribute
                if hasattr(resp, 'models'):
                    for m in getattr(resp, 'models') or []:
                        # objects have .model (name)
                        name = getattr(m, 'model', None) or getattr(m, 'name', None)
                        if isinstance(name, str):
                            models.append(name)
                # Fallback: dict with 'models'
                elif isinstance(resp, dict) and 'models' in resp:
                    for m in resp.get('models') or []:
                        if isinstance(m, dict):
                            name = m.get('name') or m.get('model')
                        else:
                            name = str(m)
                        if isinstance(name, str):
                            models.append(name)
            except Exception:
                # ignore and fallback to client
                pass
        # 2) Fallback to client.list() if needed
        if not models and self.ollama_client and hasattr(self.ollama_client, 'list'):
            try:
                resp = self.ollama_client.list()
                items = []
                if hasattr(resp, 'models'):
                    items = resp.models  # type: ignore[attr-defined]
                elif isinstance(resp, dict) and 'models' in resp:
                    items = resp['models'] or []
                elif isinstance(resp, list):
                    items = resp
                for m in items:
                    name = None
                    if isinstance(m, dict):
                        name = m.get('name') or m.get('model')
                    else:
                        name = getattr(m, 'model', None) or getattr(m, 'name', None) or (str(m) if m else None)
                    if isinstance(name, str):
                        models.append(name)
            except Exception:
                pass
        if not models:
            models = [self.model_name]
        return sorted(set(models))

    def populate_model_menu(self):
        """Load models from Ollama and update the dropdown."""
        models = self.get_available_models()
        try:
            menu = self.model_optionmenu["menu"]
            menu.delete(0, "end")
            for m in models:
                menu.add_command(label=m, command=lambda v=m: self.model_var.set(v))
            if self.model_var.get() not in models:
                self.model_var.set(models[0])
        except Exception:
            if models:
                self.model_var.set(models[0])

    def show_inline_diff(self, old_text, new_text):
        """
        Compute a diff using difflib and insert inline color-coded changes
        into the text widget. Deletions in red, additions in green.
        """
        self.text_area.delete("1.0", tk.END)

        # Split on whitespace while keeping the whitespace tokens so that
        # newline characters and other spacing are preserved in the output
        old_tokens = re.split(r'(\s+)', old_text)
        new_tokens = re.split(r'(\s+)', new_text)

        diff = difflib.ndiff(old_tokens, new_tokens)

        for token in diff:
            # token starts with '  ' (no change), '- ' (deletion), or '+ ' (addition)
            text = token[2:]
            if token.startswith("  "):
                # no change
                self.text_area.insert(tk.END, text)
            elif token.startswith("- "):
                # deletion
                self.text_area.insert(tk.END, text, ("deletion",))
            elif token.startswith("+ "):
                # addition
                self.text_area.insert(tk.END, text, ("addition",))

        # Tag styles
        self.text_area.tag_config("deletion", foreground="red")
        self.text_area.tag_config("addition", foreground="green")

    def generate_bold_diff(self, original_text, edited_text):
        """
        Generate two strings:
         - In the 'User Text', highlight removed words in bold
         - In the 'Edited Text', highlight added words in bold
        """
        # Preserve whitespace/newlines to retain formatting in scratchpad
        orig_tokens = re.split(r'(\s+)', original_text)
        edit_tokens = re.split(r'(\s+)', edited_text)

        diff = difflib.ndiff(orig_tokens, edit_tokens)
        user_text_bold = []
        edited_text_bold = []

        for token in diff:
            text = token[2:]
            if token.startswith("  "):
                user_text_bold.append(text)
                edited_text_bold.append(text)
            elif token.startswith("- "):
                # Removed: bold non-whitespace in user view
                if text.isspace() or text == "":
                    user_text_bold.append(text)
                else:
                    user_text_bold.append(f"**{text}**")
            elif token.startswith("+ "):
                # Added: bold non-whitespace in edited view
                if text.isspace() or text == "":
                    edited_text_bold.append(text)
                else:
                    edited_text_bold.append(f"**{text}**")

        return "".join(user_text_bold), "".join(edited_text_bold)

    # --------------
    # Accept / Reject changes
    # --------------
    def accept_all_changes(self):
        """Accept all changes by removing diff markup and using the 'plus' words only."""
        final_text = self.get_text_excluding_tag_safe("deletion")
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", final_text)

        # Log acceptance
        self.log_to_scratchpad("User accepted all changes.\n\n")

    def reject_all_changes(self):
        """Reject all changes by removing diff markup and using the 'original' words only."""
        final_text = self.get_text_excluding_tag_safe("addition")
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", final_text)

        # Log rejection
        self.log_to_scratchpad("User rejected all changes.\n\n")

    def get_text_excluding_tag(self, tag):
        """
        Helper to rebuild text from the text widget while excluding a particular tagâ€™s text.
        """
        result = ""
        idx = "1.0"
        while True:
            if float(self.text_area.index(idx)) >= float(self.text_area.index(tk.END)):
                break

            char = self.text_area.get(idx)
            current_tags = self.text_area.tag_names(idx)
            if tag not in current_tags:
                result += char

            idx = self.text_area.index(f"{idx}+1c")
            if idx == self.text_area.index(tk.END):
                break

        return result

    # --------------
    # Logging / Scratchpad
    # --------------
    def log_to_scratchpad(self, *texts):
        """Write changes and actions to the scratchpad file."""
        if not self.scratchpad_filename:
            return
        with open(self.scratchpad_filename, "a", encoding="utf-8") as f:
            for text in texts:
                f.write(text)
            f.write("\n")

    def get_text_excluding_tag_safe(self, tag):
        """Rebuild text while excluding characters belonging to a given tag."""
        result = []
        idx = "1.0"
        end_idx = self.text_area.index("end-1c")
        while self.text_area.compare(idx, "<", end_idx):
            char = self.text_area.get(idx)
            current_tags = self.text_area.tag_names(idx)
            if tag not in current_tags:
                result.append(char)
            idx = self.text_area.index(f"{idx}+1c")
        return "".join(result)


# --------------
# Main entry point
# --------------
if __name__ == "__main__":
    root = tk.Tk()
    app = EditorApp(root)
    root.mainloop()

