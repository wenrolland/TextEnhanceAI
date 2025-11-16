# TextEnhanceAI - Editor with Local LLM Integration

A user-friendly, Python-based editor that leverages a locally hosted LLM (via [Ollama](https://github.com/jmorganca/ollama)) for fast text enhancements, proofreading, and rewriting. Whether you're polishing a blog post, correcting grammar, or simplifying your wording, this editor lets you use local generative AI right from your desktop — no cloud services needed.

![App Window - v0.12](https://github.com/wenrolland/TextEnhanceAI/blob/main/TextEnhanceAI-v0.12.png)

## Key Features

**1. Inline Editing and Diff View**  
   - Type or paste your plain text into the editor, then click an editing action (Grammar, Proofread, Rewrite, etc.).  
   - The application compares your text against the AI-edited output and highlights changes inline.  
   - Deletions appear in red, additions in green.

**2. Multiple Editing Modes**  
   - Built-in prompts let you quickly fix grammar, streamline awkward phrases, or make your text more concise.  
   - A customizable "Custom Prompt" option allows you to craft specialized instructions for the LLM.

**3. Model Selection (v0.12)**  
   - Choose any locally downloaded Ollama model from the Model dropdown at the top.  
   - Click Refresh to reload the list after adding/removing models in Ollama.

**4. Accept / Reject All Changes**  
   - Quickly apply all AI-suggested edits with "Accept All Changes," or revert them entirely with "Reject All Changes."  

**5. Scratchpad Logging**  
   - Every edit is logged to a Markdown scratchpad file.  
   - The original user text and the LLM's edited text are saved side by side, with removed/added words highlighted in bold Markdown, helping you track changes over time.

**6. Local LLM Support**  
   - Connects to a locally hosted LLM through Ollama.  
   - No internet connection required — your content stays on your own machine.

## Getting Started

**1. Install Requirements**  
   - Ensure Python 3.7+ is installed.  
   - Install the Ollama Python package: `pip install ollama`.  
   - Pull a model in Ollama
      - If you have a GPU with 6 to 8 gb of VRAM : `ollama pull llama3.1:8b`
      - If you don't have a GPU: `ollama pull qwen3:1.7b`.

**2. Using uv (optional if installed)**  
   - `cd TextEnhanceAI`  
   - Create venv: `uv venv`  
   - Install deps: `uv pip install -r requirements.txt`  
   - Run: `uv run python TextEnhanceAI.py`

**3. Run the App**  
   - Launch with: `python TextEnhanceAI.py`  
   - If Ollama is running, you'll see the main editor window.

**4. Use the Editing Buttons**  
   - Type or paste your text in any language supported by your LLMs.  
   - Click an editing button (e.g., "Grammar", "Proofread").  
   - The edited text is displayed inline, with changes highlighted.
   - Choose the LLM from the Model dropdown (defaults to `llama3.1:8b`). Use the Refresh button to reload locally available models from Ollama.

## Contact

**Email**: [wenrolland@designecologique.ca](mailto:wenrolland@designecologique.ca)

---

## Updates

**Version 0.12**: Adds Model dropdown to choose local Ollama models and improves status text.  
**Version 0.11**: Fixes formatting to keep line breaks after editing.

