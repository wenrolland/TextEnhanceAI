import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, simpledialog
import difflib
import re
from datetime import datetime
import textwrap
import os

try:
    from ollama import Client
except ImportError:
    print("Please install the ollama package (pip install ollama).")
    Client = None

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
# Custom dialog to allow an 80-character-wide prompt entry
# --------------
class LargerPromptDialog(simpledialog._QueryString):
    def body(self, master):
        # Let the superclass build the main layout
        super().body(master)
        # Force the entry to be a wider text field
        self.entry.config(width=80)

def ask_custom_string(title, prompt, parent=None):
    """Ask for a string in a custom 80-char wide prompt dialog."""
    d = LargerPromptDialog(title, prompt)
    return d.result


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
        self.root.title("TextEnhanceAI Editor with Local LLM - V 0.1")

        # ----------------------
        # 1) Set starting size and use it as the minimum
        # ----------------------
        self.root.geometry("800x600")
        self.root.minsize(800, 600)

        # Ollama client (make sure you've installed and are running your local LLM server)
        self.ollama_client = Client() if Client else None

        # Text area (scrolled)
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=80, height=25)
        self.text_area.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Frame for buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

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
        
        # We store the “diff-annotated” version of the text in a separate place
        # so we can choose to accept or reject changes piecewise.
        self.diff_text = ""
        self.temp_html = ""  # If you want to store a temporary HTML version

        # For scratchpad logging:
        self.scratchpad_filename = None
        self.first_change_time = None

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
        self.query_llm_and_show_diff(user_text, prompt_text)

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
            self.query_llm_and_show_diff(user_text, custom_prompt)

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
            self.query_llm_and_show_diff(user_text, translate_prompt)

    # --------------
    # LLM + diff logic
    # --------------
    def query_llm_and_show_diff(self, user_text, instruction):
        """
        Calls the local LLM with user_text + instruction,
        receives an edited version, compares them, and highlights changes.
        Also logs to scratchpad with bold Markdown for the changes.
        """
        # If it's the first time we are modifying text, create the scratchpad
        if not self.first_change_time:
            self.first_change_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.scratchpad_filename = f"TextEnhanceAI-scratchpad_{self.first_change_time}.md"

        # Prepare the conversation
        system_prompt = (
            "You are a helpful, concise assistant that carefully edits text "
            "based on instructions. Return only the edited text, without extra commentary."
        )
        history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Instruction:\n{instruction}\n\nText:\n{user_text}"}
        ]

        response = {}
        try:
            response = self.ollama_client.chat(
                model="llama3.1:8b",  # Adjust to your local model or naming
                messages=history,
                options={
                    'num_predict': 2048,
                    'temperature': 0.7,
                    'top_p': 0.9,
                },
            )
        except Exception as e:
            messagebox.showerror("LLM Error", f"An error occurred: {e}")
            return

        # The "message" content from the LLM (the new text)
        edited_text = ""
        if "message" in response and "content" in response["message"]:
            edited_text = response["message"]["content"].strip()
        else:
            messagebox.showinfo("LLM Error", "No content received from LLM.")
            return

        # Show inline diff to the text widget
        self.show_inline_diff(user_text, edited_text)

        # Log to scratchpad with bold for differences
        bold_user_text, bold_edited_text = self.generate_bold_diff(user_text, edited_text)
        self.log_to_scratchpad(
            f"#Instruction: {instruction} #\n\n"
            f"##User Text:##\n{bold_user_text}\n\n"
            f"##Edited Text:##\n{bold_edited_text}\n\n"
        )

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
        diff = difflib.ndiff(original_text.split(), edited_text.split())
        
        user_text_bold = []
        edited_text_bold = []

        for token in diff:
            if token.startswith("  "):
                # No change
                word = token[2:]
                user_text_bold.append(word)
                edited_text_bold.append(word)
            elif token.startswith("- "):
                # Removed word
                word = token[2:]
                user_text_bold.append(f"**{word}**")
            elif token.startswith("+ "):
                # Added word
                word = token[2:]
                edited_text_bold.append(f"**{word}**")

        # Rebuild as strings
        return " ".join(user_text_bold), " ".join(edited_text_bold)

    # --------------
    # Accept / Reject changes
    # --------------
    def accept_all_changes(self):
        """Accept all changes by removing diff markup and using the 'plus' words only."""
        final_text = self.get_text_excluding_tag("deletion")
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", final_text)

        # Log acceptance
        self.log_to_scratchpad("User accepted all changes.\n\n")

    def reject_all_changes(self):
        """Reject all changes by removing diff markup and using the 'original' words only."""
        final_text = self.get_text_excluding_tag("addition")
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", final_text)

        # Log rejection
        self.log_to_scratchpad("User rejected all changes.\n\n")

    def get_text_excluding_tag(self, tag):
        """
        Helper to rebuild text from the text widget while excluding a particular tag’s text.
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
    def log_to_scratchpad(self, text):
        """Write changes and actions to the scratchpad file."""
        if not self.scratchpad_filename:
            return
        with open(self.scratchpad_filename, "a", encoding="utf-8") as f:
            f.write(text + "\n")


# --------------
# Main entry point
# --------------
if __name__ == "__main__":
    root = tk.Tk()
    app = EditorApp(root)
    root.mainloop()
