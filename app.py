# -*- coding: utf-8 -*-
"""
GameDistribution Page Source Parser
========================

Click CTRL + U in Game Page,
Past All Code in the app.

Author: ALI MARESH
License: MIT
"""

import tkinter as tk
from tkinter import ttk, filedialog
from tkinter import messagebox
import json
import time
import io
import urllib.request
import urllib.error
import webbrowser

# Optional libraries check
MISSING = []
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None
    MISSING.append('bs4 (beautifulsoup4)')

try:
    import pyperclip
except Exception:
    pyperclip = None
    MISSING.append('pyperclip')

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None
    MISSING.append('Pillow (PIL)')

# Dark Theme Configuration
THEME = {
    'bg': '#071018',
    'panel': '#0b1220',
    'input_bg': '#071017',
    'text': '#e6eef6',
    'muted': '#8b98a4',
    'accent_purple': '#7c3aed',
    'accent_green': '#10b981',
    'accent_red': '#ef4444',
    'accent_yellow': '#f59e0b'
}

class SimpleNotifier:
    """A simple toast notification system."""
    def __init__(self, root):
        self.root = root

    def show(self, title, message, kind='info'):
        # Use a small toplevel window instead of messagebox to match the theme
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes('-topmost', True)
        toast.configure(bg=THEME['panel'])
        
        full_text = f"{title}: {message}" if title else message
        lbl = tk.Label(toast, text=full_text, bg=THEME['panel'], fg=THEME['text'], justify='left', font=('Segoe UI', 9))
        lbl.pack(padx=12, pady=8)
        
        toast.update_idletasks()
        # Center at the top of the main window
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (toast.winfo_width() // 2)
        y = self.root.winfo_y() + 50
        toast.geometry(f"+{x}+{y}")
        
        # Auto-close after 2 seconds
        toast.after(2000, toast.destroy)

def extract_from_html_source(html_text):
    """Extracts game data from the GameDistribution HTML source."""
    if BeautifulSoup is None:
        raise RuntimeError('Library "beautifulsoup4" is not installed. Install it via: pip install beautifulsoup4')

    soup = BeautifulSoup(html_text, 'html.parser')
    script_tag = soup.find('script', id='__NEXT_DATA__')
    if not script_tag or not script_tag.string:
        raise ValueError('JSON data not found in the page source.')

    data = json.loads(script_tag.string)
    game = data.get('props', {}).get('pageProps', {}).get('game', {})

    object_id = game.get('objectID', '')
    title = game.get('title', '')
    description = game.get('description', '').strip()
    instructions = game.get('instruction', '').strip()
    width = str(game.get('width', ''))
    height = str(game.get('height', ''))
    category = ', '.join(game.get('categories', []))
    tags = ', '.join(game.get('tags', []))

    thumb = ''
    for asset in game.get('assets', []):
        if isinstance(asset, dict) and '512x512' in asset.get('name', ''):
            thumb = f"https://img.gamedistribution.com/{asset['name']}"
            break

    url_game = f"https://html5.gamedistribution.com/{object_id}/" if object_id else ''

    return {
        'id': object_id,
        'title': title,
        'description': description,
        'instructions': instructions,
        'url': url_game,
        'category': category,
        'tags': tags,
        'thumb': thumb,
        'width': width,
        'height': height
    }

class App:
    def __init__(self, root):
        self.root = root
        self.root.title('🎮 GameDistribution JSON Parser')
        self.root.geometry('1050x760')
        self.root.configure(bg=THEME['bg'])

        self.notifier = SimpleNotifier(root)
        self._build_ui()

        if MISSING:
            missing_text = ', '.join(MISSING)
            self.notifier.show('Missing Libraries', f'Please install: {missing_text}', kind='warning')

    def _build_ui(self):
        # Header
        top = tk.Frame(self.root, bg=THEME['panel'])
        top.pack(fill='x', padx=10, pady=10)
        tk.Label(top, text='GameDistribution Parser', bg=THEME['panel'], fg=THEME['accent_purple'], font=('Segoe UI', 14, 'bold')).pack(side='left')

        # Toolbar
        toolbar = tk.Frame(self.root, bg=THEME['bg'])
        toolbar.pack(fill='x', padx=10)
        
        self._create_button(toolbar, 'Extract (Ctrl+E)', self.on_extract, THEME['accent_purple'])
        self._create_button(toolbar, 'Copy JSON (Ctrl+C)', self.on_copy, THEME['accent_green'])
        self._create_button(toolbar, 'Save JSON', self.save_json, THEME['accent_purple'])
        self._create_button(toolbar, 'Clear (Ctrl+L)', self.clear, THEME['accent_red'])

        # Main Content
        main = tk.Frame(self.root, bg=THEME['bg'])
        main.pack(fill='both', expand=True, padx=10, pady=10)

        # Left Panel: Input
        left = tk.Frame(main, bg=THEME['bg'])
        left.pack(side='left', fill='both', expand=True)
        tk.Label(left, text='Paste Page Source Here', bg=THEME['bg'], fg=THEME['text']).pack(anchor='w')
        
        self.text_input = tk.Text(left, bg=THEME['input_bg'], fg=THEME['text'], insertbackground='white', font=('Consolas', 10), wrap='word', height=40)
        self.text_input.pack(fill='both', expand=False, pady=10)

        # Right Panel: Output & Preview
        right = tk.Frame(main, bg=THEME['bg'], width=360)
        right.pack(side='right', fill='y', padx=(10, 0))

        tk.Label(right, text='Game Thumbnail', bg=THEME['bg'], fg=THEME['muted']).pack(anchor='w')
        self.thumb_canvas = tk.Canvas(right, width=220, height=220, bg=THEME['panel'], highlightthickness=0)
        self.thumb_canvas.pack(pady=8)
        self._thumb_img_ref = None
        self._draw_thumb_placeholder()

        self.open_img_btn = tk.Button(right, text='Open Image in Browser', command=self.open_image_in_browser, bg=THEME['accent_purple'], fg='white', bd=0, padx=8, pady=6)
        self.open_img_btn.pack(pady=(0, 8))

        tk.Label(right, text='Result (JSON)', bg=THEME['bg'], fg=THEME['muted']).pack(anchor='w')
        self.text_output = tk.Text(right, bg=THEME['panel'], fg='#a7f3d0', insertbackground='white', font=('Consolas', 10), wrap='none', height=21)
        self.text_output.pack(fill='both', expand=False)

        # Status Bar
        status = tk.Frame(self.root, bg=THEME['panel'])
        status.pack(fill='x', padx=10, pady=(6, 10))
        self.status_var = tk.StringVar(value='Ready')
        tk.Label(status, textvariable=self.status_var, bg=THEME['panel'], fg=THEME['muted']).pack(side='left')

        # Shortcuts
        self.root.bind_all('<Control-e>', lambda e: self.on_extract())
        self.root.bind_all('<Control-E>', lambda e: self.on_extract())
        self.root.bind_all('<Control-c>', lambda e: self.on_copy())
        self.root.bind_all('<Control-C>', lambda e: self.on_copy())
        self.root.bind_all('<Control-l>', lambda e: self.clear())
        self.root.bind_all('<Control-L>', lambda e: self.clear())

    def _create_button(self, parent, text, command, bg_color):
        tk.Button(parent, text=text, command=command, bg=bg_color, fg='white', bd=0, padx=12, pady=6).pack(side='left', padx=6)

    def _draw_thumb_placeholder(self):
        self.thumb_canvas.delete('all')
        self._thumb_img_ref = None
        self.thumb_canvas.create_text(110, 110, text='No Image', fill=THEME['muted'], font=('Segoe UI', 10), justify='center')
        self._current_thumb_url = None

    def _load_thumbnail(self, url):
        self.thumb_canvas.delete('all')
        self._current_thumb_url = url
        if not url:
            self._draw_thumb_placeholder()
            return

        if Image is None or ImageTk is None:
            self.thumb_canvas.create_text(110, 90, text='Image Available', fill=THEME['text'], font=('Segoe UI', 10), justify='center')
            self.thumb_canvas.create_text(110, 130, text='Install Pillow to view', fill=THEME['muted'], font=('Segoe UI', 8), justify='center')
            return

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                
            img = Image.open(io.BytesIO(data)).convert('RGBA')
            img.thumbnail((200, 200), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._thumb_img_ref = photo
            self.thumb_canvas.create_image(110, 110, image=photo)
        except urllib.error.HTTPError as e:
            self.thumb_canvas.create_text(110, 90, text=f'HTTP Error: {e.code}', fill=THEME['accent_red'], font=('Segoe UI', 10), justify='center')
        except Exception as e:
            self.thumb_canvas.create_text(110, 90, text='Error loading image', fill=THEME['accent_red'], font=('Segoe UI', 10), justify='center')
            self.thumb_canvas.create_text(110, 130, text=str(e), fill=THEME['muted'], font=('Segoe UI', 8), justify='center')

    def open_image_in_browser(self):
        if getattr(self, '_current_thumb_url', None):
            webbrowser.open(self._current_thumb_url)
        else:
            self.notifier.show('Warning', 'No image URL to open')

    def on_extract(self):
        html_text = self.text_input.get('1.0', tk.END).strip()
        if not html_text:
            self.notifier.show('Warning', 'Please paste the page source first')
            self.status_var.set('No input')
            return
        try:
            self.status_var.set('Extracting...')
            result = extract_from_html_source(html_text)
            json_text = json.dumps(result, ensure_ascii=False, indent=2)
            self.text_output.delete('1.0', tk.END)
            self.text_output.insert('1.0', json_text)
            
            thumb = result.get('thumb')
            if thumb:
                self._load_thumbnail(thumb)
            else:
                self._draw_thumb_placeholder()
                
            self.notifier.show('Success', 'Extraction complete', kind='success')
            self.status_var.set('Extraction complete')
        except Exception as e:
            self.notifier.show('Error', str(e), kind='error')
            self.status_var.set('Error occurred')

    def on_copy(self):
        content = self.text_output.get('1.0', tk.END).strip()
        if not content:
            self.notifier.show('Warning', 'No data to copy')
            return
        if pyperclip is None:
            self.notifier.show('Error', 'pyperclip library is not installed')
            return
        try:
            pyperclip.copy(content)
            self.notifier.show('Copied', 'JSON copied to clipboard')
            self.status_var.set('Copied to clipboard')
        except Exception:
            self.notifier.show('Error', 'Failed to copy')
            self.status_var.set('Copy failed')

    def clear(self):
        self.text_input.delete('1.0', tk.END)
        self.text_output.delete('1.0', tk.END)
        self._draw_thumb_placeholder()
        self.notifier.show('Cleared', 'All data cleared')
        self.status_var.set('Ready')

    def save_json(self):
        content = self.text_output.get('1.0', tk.END).strip()
        if not content:
            self.notifier.show('Warning', 'No data to save')
            return
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON files', '*.json')])
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.notifier.show('Saved', 'File saved successfully')
            except Exception as e:
                self.notifier.show('Error', 'Failed to save file')

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
