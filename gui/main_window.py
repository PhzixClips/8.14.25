"""
Main application window and GUI controller (no presets, free-form Count)
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
import webview
from typing import Optional

# --- App config & theme ---
from config import WINDOW_GEOMETRY, COLORS, UI_FONT_FAMILY, UI_FONT_SIZES
from gui.theme import apply_theme
from gui.settings_window import SettingsWindow

# Core modules
from search.search_engine import SearchEngine
from media.media_processor import MediaProcessor
from analysis.video_analyzer import VideoAnalyzer
from gui.tab_manager import TabManager
from gui.components import (
    ProgressDialog, CaptionDialog, TranscriptDialog, TimerWidget
)
from utils.logging import Logger

# Winners (fallback if module not present)
try:
    from data.winners_manager import WinnersManager
except ImportError:
    class WinnersManager:
        def __init__(self, *_, **__): self.winners=[]
        def get_winner_count(self): return 0
        def get_all_folders(self): return ["Default"]
        def add_winner(self, *_, **__): return False
        def get_winner_by_id(self, *_, **__): return None
        def add_folder(self, *_, **__): return False


class MainWindow:
    """Main application window controller"""

    def __init__(self):
        self.logger = Logger("MainWindow")

        # Initialize components
        self.search_engine = SearchEngine()
        self.winners_manager = WinnersManager()
        self.media_processor = MediaProcessor()

        # UI components
        self.root = None
        self.tab_manager = None
        self.progress_dialog = None
        self.timer_widget = None

        # Search state
        self.current_search_active = False

        # --- Widget references for dynamic updates ---
        self.url_label = None
        self.url_entry = None

        # Search & Filter Frames
        self.search_controls_frame = None
        self.winners_filter_frame = None

        self.query_label = None
        self.query_entry = None
        self.uploaded_label = None
        self.date_combo = None
        self.count_label = None
        self.count_entry = None
        self.vph_label = None
        self.vph_entry = None
        self.max_duration_label = None
        self.max_duration_entry = None
        self.generate_button = None

        # Winners Filter Widgets
        self.folder_filter_label = None
        self.folder_filter_combo = None

        self.action_buttons = {}
        self.winners_counter_label = None
        self.tab_counter_label = None


    # -----------------------------
    # App lifecycle
    # -----------------------------
    def run(self):
        self._create_gui()
        self.root.mainloop()

    def _create_gui(self):
        self.root = tk.Tk()
        self.root.title('YouTube Clip Agent - Modular Edition')
        self.root.geometry(WINDOW_GEOMETRY)

        # Apply global ttk theme + scaling BEFORE creating ttk widgets
        try:
            apply_theme(self.root)
        except Exception as e:
            self.logger.error(f"Theme apply error (continuing with defaults): {e}")

        # Create main components
        self._create_url_input()
        self._create_search_controls()
        self._create_winners_filter_controls()  # Add this
        self._create_tab_system()
        self._create_action_buttons()
        self._create_status_bar()

        # Apply settings (styles, fonts, colors)
        self._apply_live_settings()

        # Initialize Winners tab and load data
        self._initialize_winners_tab()
        self._update_folder_filter_options()

        # Initial results tab
        self.tab_manager.add_new_tab("Search Results")

        self.logger.info("GUI initialized successfully")

    # -----------------------------
    # Styles & Settings Application
    # -----------------------------
    def _apply_live_settings(self):
        """Applies settings that can be changed dynamically."""
        # Reload settings in case they changed
        from config import COLORS, UI_FONT_FAMILY, UI_FONT_SIZES

        self.root.configure(bg=COLORS.get('bg_primary', '#16181d'))
        self._configure_styles(COLORS, UI_FONT_FAMILY, UI_FONT_SIZES)
        self._update_widget_fonts(COLORS, UI_FONT_FAMILY, UI_FONT_SIZES)

    def _configure_styles(self, colors, font_family, font_sizes):
        """Configure ttk styles with current palette and fix white-on-white"""
        style = ttk.Style()

        font_sm = (font_family, font_sizes['sm'])
        font_sm_bold = (font_family, font_sizes['sm'], 'bold')

        # Treeview base
        style.configure(
            'Treeview',
            background=colors.get('bg_primary', '#16181d'),
            foreground=colors.get('fg_primary', '#e6e6e6'),
            fieldbackground=colors.get('bg_secondary', '#1f232a'),
            rowheight=24,
            font=font_sm
        )
        style.map(
            'Treeview',
            background=[('selected', colors.get('bg_accent', '#2d6cdf'))],
            foreground=[('selected', colors.get('fg_on_accent', '#ffffff'))]
        )

        # Treeview header
        style.configure(
            'Treeview.Heading',
            background=colors.get('bg_primary', '#16181d'),
            foreground=colors.get('fg_accent', '#fbbf24'),
            relief='flat',
            font=font_sm_bold
        )

        # Buttons
        style.configure('TButton', padding=(10, 6), font=font_sm)
        style.map('TButton', relief=[('pressed', 'sunken'), ('active', 'raised')])

        # Dark combobox style
        style_name = 'Dark.TCombobox'
        style.configure(
            style_name,
            fieldbackground=colors.get('bg_secondary', '#1f232a'),
            background=colors.get('bg_secondary', '#1f232a'),
            foreground=colors.get('fg_primary', '#e6e6e6')
        )
        style.map(
            style_name,
            fieldbackground=[('readonly', colors.get('bg_secondary', '#1f232a')),
                             ('!disabled', colors.get('bg_secondary', '#1f232a'))],
            foreground=[('readonly', colors.get('fg_primary', '#e6e6e6')),
                        ('!disabled', colors.get('fg_primary', '#e6e6e6'))],
            background=[('active', colors.get('bg_secondary', '#1f232a'))]
        )
        self.combobox_style = style_name

    def _update_widget_fonts(self, colors, font_family, font_sizes):
        """Update fonts for widgets that don't use ttk styles."""
        font_base = (font_family, font_sizes['base'])
        font_base_bold = (font_family, font_sizes['base'], 'bold')
        font_sm = (font_family, font_sizes['sm'])
        font_sm_bold = (font_family, font_sizes['sm'], 'bold')

        # URL Input
        if self.url_label: self.url_label.config(font=font_base_bold)
        if self.url_entry: self.url_entry.config(font=font_base)

        # Search Controls
        if self.query_label: self.query_label.config(font=font_sm)
        if self.query_entry: self.query_entry.config(font=font_sm)
        if self.uploaded_label: self.uploaded_label.config(font=font_sm)
        if self.count_label: self.count_label.config(font=font_sm)
        if self.count_entry: self.count_entry.config(font=font_sm)
        if self.vph_label: self.vph_label.config(font=font_sm)
        if self.vph_entry: self.vph_entry.config(font=font_sm)
        if self.max_duration_label: self.max_duration_label.config(font=font_sm)
        if self.max_duration_entry: self.max_duration_entry.config(font=font_sm)
        if self.generate_button: self.generate_button.config(font=font_base_bold)

        # Winners Filter
        if hasattr(self, 'folder_filter_label') and self.folder_filter_label:
            self.folder_filter_label.config(font=font_sm)

        # Action Buttons
        for text, button in self.action_buttons.items():
            is_winner_btn = text.startswith('🏆')
            button.config(font=font_sm_bold if is_winner_btn else font_sm)

        # Status Bar
        if self.winners_counter_label: self.winners_counter_label.config(font=font_sm_bold)
        if self.tab_counter_label: self.tab_counter_label.config(font=font_sm)

    # -----------------------------
    # Top: URL section
    # -----------------------------
    def _create_url_input(self):
        url_frame = tk.Frame(self.root, bg=COLORS.get('bg_primary', '#16181d'))
        url_frame.pack(fill='x', padx=10, pady=(8, 4))

        self.url_label = tk.Label(url_frame, text='🔗 YouTube URL:', bg=COLORS.get('bg_primary', '#16181d'), fg=COLORS.get('fg_accent', '#fbbf24'))
        self.url_label.pack(side='left')

        self.url_entry = tk.Entry(url_frame, width=60, bg=COLORS.get('bg_secondary', '#1f232a'), fg=COLORS.get('fg_primary', '#e6e6e6'), insertbackground=COLORS.get('fg_primary', '#e6e6e6'))
        self.url_entry.pack(side='left', padx=8)

        ttk.Button(url_frame, text='🎯 Analyze URL', command=self._analyze_url).pack(side='left', padx=6)

        tk.Button(url_frame, text='🗑️', bg='#666666', fg=COLORS.get('fg_primary', '#e6e6e6'), command=self._clear_url, width=3).pack(side='left', padx=4)

        separator = tk.Frame(self.root, height=2, bg=COLORS.get('border', '#3a3a3a'))
        separator.pack(fill='x', padx=10, pady=(6, 8))

    # -----------------------------
    # Search controls row
    # -----------------------------
    def _create_search_controls(self):
        self.search_controls_frame = tk.Frame(self.root, bg=COLORS.get('bg_primary', '#16181d'))
        self.search_controls_frame.pack(fill='x', padx=10, pady=4)
        frame = self.search_controls_frame

        self.query_label = tk.Label(frame, text='Search:', bg=COLORS.get('bg_primary', '#16181d'), fg=COLORS.get('fg_primary', '#e6e6e6'))
        self.query_label.pack(side='left')
        self.query_entry = tk.Entry(frame, width=25, bg=COLORS.get('bg_secondary', '#1f232a'), fg=COLORS.get('fg_primary', '#e6e6e6'), insertbackground=COLORS.get('fg_primary', '#e6e6e6'))
        self.query_entry.pack(side='left', padx=6)

        self.uploaded_label = tk.Label(frame, text='Uploaded:', bg=COLORS.get('bg_primary', '#16181d'), fg=COLORS.get('fg_primary', '#e6e6e6'))
        self.uploaded_label.pack(side='left', padx=(12, 0))
        self.date_combo = ttk.Combobox(frame, values=['Any', '24h', '2d', '7d'], width=5, state="readonly")
        self.date_combo.set('Any')
        self.date_combo.pack(side='left', padx=6)

        self.count_label = tk.Label(frame, text='Count:', bg=COLORS.get('bg_primary', '#16181d'), fg=COLORS.get('fg_primary', '#e6e6e6'))
        self.count_label.pack(side='left', padx=(12, 0))
        self.count_entry = tk.Entry(frame, width=6, bg=COLORS.get('bg_secondary', '#1f232a'), fg=COLORS.get('fg_primary', '#e6e6e6'), insertbackground=COLORS.get('fg_primary', '#e6e6e6'))
        self.count_entry.insert(0, "50")
        self.count_entry.pack(side='left', padx=6)

        self.vph_label = tk.Label(frame, text='Min VPH:', bg=COLORS.get('bg_primary', '#16181d'), fg=COLORS.get('fg_primary', '#e6e6e6'))
        self.vph_label.pack(side='left', padx=(12, 0))
        self.vph_entry = tk.Entry(frame, width=6, bg=COLORS.get('bg_secondary', '#1f232a'), fg=COLORS.get('fg_primary', '#e6e6e6'), insertbackground=COLORS.get('fg_primary', '#e6e6e6'))
        self.vph_entry.pack(side='left', padx=6)

        self.max_duration_label = tk.Label(frame, text='Max Duration (s):', bg=COLORS.get('bg_primary', '#16181d'), fg=COLORS.get('fg_primary', '#e6e6e6'))
        self.max_duration_label.pack(side='left', padx=(12, 0))
        self.max_duration_entry = tk.Entry(frame, width=6, bg=COLORS.get('bg_secondary', '#1f232a'), fg=COLORS.get('fg_primary', '#e6e6e6'), insertbackground=COLORS.get('fg_primary', '#e6e6e6'))
        self.max_duration_entry.pack(side='left', padx=6)

        self.generate_button = tk.Button(frame, text='Generate', bg=COLORS.get('success', 'green'), fg=COLORS.get('fg_on_accent', '#ffffff'), command=self._start_search)
        self.generate_button.pack(side='left', padx=10)

    def _create_winners_filter_controls(self):
        """Creates the dropdown for filtering winners by folder."""
        self.winners_filter_frame = tk.Frame(self.root, bg=COLORS.get('bg_primary', '#16181d'))

        self.folder_filter_label = tk.Label(self.winners_filter_frame, text='Filter by Folder:', bg=COLORS.get('bg_primary', '#16181d'), fg=COLORS.get('fg_primary', '#e6e6e6'))
        self.folder_filter_label.pack(side='left', padx=(10, 0))

        self.folder_filter_combo = ttk.Combobox(self.winners_filter_frame, values=['All'], width=20, state="readonly")
        self.folder_filter_combo.set('All')
        self.folder_filter_combo.pack(side='left', padx=6)
        self.folder_filter_combo.bind('<<ComboboxSelected>>', self._on_folder_filter_changed)

        # Initially hidden
        self.winners_filter_frame.pack(fill='x', padx=10, pady=4)
        self.winners_filter_frame.pack_forget()

    # -----------------------------
    # Tabs + results table
    # -----------------------------
    def _create_tab_system(self):
        self.tree_container = tk.Frame(self.root, bg=COLORS.get('bg_primary', '#16181d'))
        self.tree_container.pack(fill='both', expand=True, padx=8, pady=8)
        self.tab_manager = TabManager(self.root, self.tree_container, on_tab_switch_callback=self._on_tab_switched)

    # -----------------------------
    # Bottom action buttons
    # -----------------------------
    def _create_action_buttons(self):
        button_frame = tk.Frame(self.root, bg=COLORS.get('bg_primary', '#16181d'))
        button_frame.pack(fill='x', pady=6)

        left_frame = tk.Frame(button_frame, bg=COLORS.get('bg_primary', '#16181d'))
        left_frame.pack(side='left')

        buttons = [
            ('Preview', '#3B82F6', self._preview_video),
            ('Download', '#3B82F6', self._download_video),
            ('Transcribe', '#7C3AED', self._transcribe_video),
            ('Find Raw', '#A16207', self._find_raw_source),
            ('🏆 Save to Winners', '#FFD700', self._save_to_winners),
            ('Open Folder', '#222', self._open_clip_folder)
        ]

        for text, color, command in buttons:
            btn = tk.Button(left_frame, text=text, bg=color, fg=('#000' if text.startswith('🏆') else COLORS.get('fg_on_accent', '#ffffff')), command=command, padx=10, pady=6, relief='flat', bd=0)
            btn.pack(side='left', padx=6)
            self.action_buttons[text] = btn

    # -----------------------------
    # Status bar
    # -----------------------------
    def _create_status_bar(self):
        status_frame = tk.Frame(self.root, bg=COLORS.get('bg_primary', '#16181d'))
        status_frame.pack(fill='x', padx=12, pady=(0, 6))

        left_frame = tk.Frame(status_frame, bg=COLORS.get('bg_primary', '#16181d'))
        left_frame.pack(side='left')

        self.winners_counter_label = tk.Label(left_frame, text='Winners: 0', fg='#FFD700', bg=COLORS.get('bg_primary', '#16181d'))
        self.winners_counter_label.pack(side='left', padx=(0, 18))

        right_frame = tk.Frame(status_frame, bg=COLORS.get('bg_primary', '#16181d'))
        right_frame.pack(side='right', padx=10)

        self.tab_counter_label = tk.Label(right_frame, text='Tabs: 0', fg='#A3A3A3', bg=COLORS.get('bg_primary', '#16181d'))
        self.tab_counter_label.pack(side='left', padx=(0, 18))

        self.timer_widget = TimerWidget(right_frame)
        self.timer_widget.pack(side='left')

        ttk.Button(right_frame, text='Set Timer', command=self._set_timer).pack(side='left', padx=10)

        ttk.Button(right_frame, text='Settings', command=self._open_settings).pack(side='left', padx=10)

    def _open_settings(self):
        """Opens the settings window and applies changes upon closing."""
        settings_win = SettingsWindow(self.root)
        self.root.wait_window(settings_win)
        # A restart is still recommended for theme changes to be perfect
        messagebox.showinfo("Settings Updated", "Live settings applied. A restart is recommended for all changes to take full effect.", parent=self.root)
        self._apply_live_settings()

    def _on_folder_filter_changed(self, event=None):
        """Callback for when the folder filter dropdown changes."""
        selected_folder = self.folder_filter_combo.get()
        winners_tab = self.tab_manager.get_winners_tab()
        if not winners_tab:
            return

        self.tab_manager.clear_tab_results(winners_tab.tab_id)

        if selected_folder == "All":
            winners_to_display = self.winners_manager.winners
        else:
            winners_to_display = self.winners_manager.get_winners_by_folder(selected_folder)

        for winner in winners_to_display:
            self.tab_manager.add_winner_to_tab(winner.to_dict())

    def _on_tab_switched(self, tab_id: str):
        """Callback for when the active tab changes."""
        is_winners = tab_id == self.tab_manager.winners_tab_id
        if is_winners:
            if self.search_controls_frame:
                self.search_controls_frame.pack_forget()
            if self.winners_filter_frame:
                self.winners_filter_frame.pack(fill='x', padx=10, pady=4)
        else:
            if self.winners_filter_frame:
                self.winners_filter_frame.pack_forget()
            if self.search_controls_frame:
                self.search_controls_frame.pack(fill='x', padx=10, pady=4)

    def _update_folder_filter_options(self):
        """Updates the folder filter dropdown with the latest folder list."""
        if not hasattr(self, 'folder_filter_combo') or not self.folder_filter_combo:
            return
        folders = ["All"] + self.winners_manager.get_all_folders()
        self.folder_filter_combo['values'] = folders
        self.folder_filter_combo.set("All")

    # --- The rest of the file remains the same ---
    def _initialize_winners_tab(self):
        try:
            winners_tab_id = self.tab_manager.create_winners_tab()
            self._load_winners_to_tab()
            winner_count = self.winners_manager.get_winner_count()
            self.winners_counter_label.config(text=f'Winners: {winner_count}')
            self.tab_manager.update_tab_status(
                winners_tab_id,
                f"{winner_count} saved",
                'complete' if winner_count > 0 else 'idle'
            )
        except Exception as e:
            self.logger.error(f"Error initializing winners tab: {e}")

    def _load_winners_to_tab(self):
        try:
            winners_tab = self.tab_manager.get_winners_tab()
            if not winners_tab:
                return
            self.tab_manager.clear_tab_results(winners_tab.tab_id)
            for winner in self.winners_manager.winners:
                self.tab_manager.add_winner_to_tab(winner.to_dict())
        except Exception as e:
            self.logger.error(f"Error loading winners to tab: {e}")

    def _save_to_winners(self):
        try:
            video = self.tab_manager.get_selected_video()
            if not video:
                messagebox.showinfo('Save to Winners', 'Please select a video first.')
                return

            video_id = video.get('video_id', '')
            if self.winners_manager.get_winner_by_id(video_id):
                messagebox.showwarning('Already Saved', 'This video is already in your Winners!')
                return

            folders = self.winners_manager.get_all_folders()
            folder_choice = self._show_folder_selection_dialog(folders)
            if folder_choice is None:
                return

            success = self.winners_manager.add_winner(video, folder_choice)
            if success:
                winner = self.winners_manager.get_winner_by_id(video_id)
                if winner:
                    self.tab_manager.add_winner_to_tab(winner.to_dict())
                winner_count = self.winners_manager.get_winner_count()
                self.winners_counter_label.config(text=f'Winners: {winner_count}')
                winners_tab_id = self.tab_manager.winners_tab_id
                if winners_tab_id:
                    self.tab_manager.update_tab_status(winners_tab_id, f"{winner_count} saved", 'complete')
                messagebox.showinfo('Success', f'Video saved to Winners in "{folder_choice}" folder!')
            else:
                messagebox.showerror('Error', 'Failed to save video to Winners.')
        except Exception as e:
            self.logger.error(f"Error saving to winners: {e}")
            messagebox.showerror('Error', f'Error saving to winners: {e}')

    def _show_folder_selection_dialog(self, folders: list) -> Optional[str]:
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title('Select Folder')
            dialog.geometry('400x300')
            dialog.configure(bg=COLORS.get('bg_primary', '#16181d'))
            dialog.resizable(False, False)
            dialog.transient(self.root)
            dialog.grab_set()

            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (dialog.winfo_screenheight() // 2) - (300 // 2)
            dialog.geometry(f"400x300+{x}+{y}")

            result = [None]

            tk.Label(
                dialog,
                text='Choose folder for this winner:',
                bg=COLORS.get('bg_primary', '#16181d'),
                fg=COLORS.get('fg_accent', '#fbbf24'),
                font=(UI_FONT_FAMILY, UI_FONT_SIZES['lg'], 'bold')
            ).pack(pady=10)

            listbox_frame = tk.Frame(dialog, bg=COLORS.get('bg_primary', '#16181d'))
            listbox_frame.pack(fill='both', expand=True, padx=20, pady=10)

            listbox = tk.Listbox(
                listbox_frame,
                bg=COLORS.get('bg_secondary', '#1f232a'),
                fg=COLORS.get('fg_primary', '#e6e6e6'),
                selectbackground=COLORS.get('bg_accent', '#2d6cdf'),
                selectforeground=COLORS.get('fg_on_accent', '#ffffff'),
                font=(UI_FONT_FAMILY, UI_FONT_SIZES['base'])
            )
            scrollbar = tk.Scrollbar(listbox_frame, command=listbox.yview)
            listbox.configure(yscrollcommand=scrollbar.set)
            listbox.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            for folder in folders:
                listbox.insert(tk.END, folder)
            listbox.select_set(0)

            button_frame = tk.Frame(dialog, bg=COLORS.get('bg_primary', '#16181d'))
            button_frame.pack(fill='x', padx=20, pady=10)

            def on_select():
                selection = listbox.curselection()
                if selection:
                    result[0] = folders[selection[0]]
                dialog.destroy()

            def on_new_folder():
                new_folder = simpledialog.askstring('New Folder', 'Enter folder name:')
                if new_folder and new_folder.strip():
                    new_folder = new_folder.strip()
                    if self.winners_manager.add_folder(new_folder):
                        result[0] = new_folder
                        dialog.destroy()
                    else:
                        messagebox.showerror('Error', 'Folder already exists or invalid name.')

            ttk.Button(button_frame, text='Select', command=on_select).pack(side='left', padx=6)
            ttk.Button(button_frame, text='New Folder', command=on_new_folder).pack(side='left', padx=6)
            ttk.Button(button_frame, text='Cancel', command=lambda: dialog.destroy()).pack(side='right', padx=6)

            dialog.wait_window()
            return result[0]
        except Exception as e:
            self.logger.error(f"Error in folder selection dialog: {e}")
            return "Default"

    def _extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
            r'youtu\.be/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'm\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            m = re.search(pattern, url)
            if m: return m.group(1)
        return None

    def _clear_url(self):
        self.url_entry.delete(0, tk.END)

    def _analyze_url(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning('No URL', 'Please enter a YouTube URL!')
            return
        video_id = self._extract_video_id(url)
        if not video_id:
            messagebox.showerror('Invalid URL', 'Please enter a valid YouTube URL!')
            return
        if self.current_search_active:
            messagebox.showwarning('Analysis Active', 'An analysis is already in progress!')
            return

        active_tab = self.tab_manager.get_active_tab()
        if active_tab and (not active_tab.search_term or "URL:" not in active_tab.search_term):
            active_tab.search_term = f"URL: {video_id}"
            active_tab.label.config(text=f"URL: {video_id[:8]}...")
        elif not active_tab:
            self.tab_manager.add_new_tab(f"URL: {video_id}")
            active_tab = self.tab_manager.get_active_tab()
        if active_tab:
            self.tab_manager.clear_tab_results(active_tab.tab_id)

        self._perform_url_analysis(video_id)

    def _perform_url_analysis(self, video_id: str):
        self.current_search_active = True
        active_tab = self.tab_manager.get_active_tab()
        if not active_tab:
            self.current_search_active = False
            return
        try:
            self.tab_manager.update_tab_status(active_tab.tab_id, "Analyzing URL...", 'loading')
            self.progress_dialog = ProgressDialog(self.root, "🔍 Analyzing YouTube URL")
            self.progress_dialog.update_status("Fetching video data...")

            video_details_map = self.search_engine.api_client.get_video_details([video_id])
            if not video_details_map or video_id not in video_details_map:
                self._finish_url_analysis([], error="Video not found or unavailable")
                return

            self.progress_dialog.update_status("Processing video data...")
            video_details = video_details_map[video_id]
            video_entry = VideoAnalyzer.process_video_data(video_details, video_id)
            if not video_entry:
                self._finish_url_analysis([], error="Failed to process video data")
                return

            self._finish_url_analysis([video_entry])
        except Exception as e:
            self.logger.error(f"URL analysis error: {e}")
            self._finish_url_analysis([], error=str(e))

    def _finish_url_analysis(self, results, error=None):
        self.current_search_active = False
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        active_tab = self.tab_manager.get_active_tab()
        if not active_tab: return

        try:
            if error:
                self.tab_manager.update_tab_status(active_tab.tab_id, "Error", 'error')
                messagebox.showerror("❌ Analysis Error", f"Error analyzing URL: {error}")
                return

            for video in results:
                self.tab_manager.add_result_to_tab(active_tab.tab_id, video)

            if results:
                video_title = results[0].get('title', 'Unknown')[:30]
                self.tab_manager.update_tab_status(active_tab.tab_id, f"✓ {video_title}...", 'complete')
                messagebox.showinfo("✅ Analysis Complete", f"Successfully analyzed video:\n{video_title}")
            else:
                self.tab_manager.update_tab_status(active_tab.tab_id, "No data", 'error')
                messagebox.showwarning("⚠️ No Data", "No video data found")

            self.tab_counter_label.config(text=f"Tabs: {self.tab_manager.get_tab_count()}")
        except Exception as e:
            self.logger.error(f"Error finishing URL analysis: {e}")
            self.tab_manager.update_tab_status(active_tab.tab_id, "Error", 'error')

    def _start_search(self):
        if self.current_search_active:
            messagebox.showwarning('Search Active', 'A search is already in progress!')
            return

        query = self.query_entry.get().strip()
        if not query:
            messagebox.showwarning('No Query', 'Please enter a search query!')
            return

        active_tab = self.tab_manager.get_active_tab()
        if active_tab and (not active_tab.search_term or active_tab.search_term != query):
            active_tab.search_term = query
            active_tab.label.config(text=query[:15] + "..." if len(query) > 15 else query)
        elif not active_tab:
            self.tab_manager.add_new_tab(query)
            active_tab = self.tab_manager.get_active_tab()
        if active_tab:
            self.tab_manager.clear_tab_results(active_tab.tab_id)

        self._perform_search(query)

    def _perform_search(self, query: str):
        self.current_search_active = True
        active_tab = self.tab_manager.get_active_tab()
        if not active_tab:
            self.current_search_active = False
            return

        try:
            self.tab_manager.update_tab_status(active_tab.tab_id, "Searching...", 'loading')

            self.progress_dialog = ProgressDialog(self.root, "🔍 Search in Progress")
            try:
                self.progress_dialog.set_cancel_callback(self._cancel_search)
            except Exception:
                pass

            self.search_engine.reset_search()

            published_after = self._get_published_after()
            try:
                max_duration = int(self.max_duration_entry.get()) if self.max_duration_entry.get() else None
            except ValueError:
                max_duration = None

            try:
                desired_count = int(self.count_entry.get().strip() or "0")
            except ValueError:
                desired_count = 0

            try:
                min_vph = float(self.vph_entry.get() or 0)
            except ValueError:
                min_vph = 0.0

            def progress_callback(found_count, total_target, status_text=None):
                if self.progress_dialog:
                    if status_text:
                        self.progress_dialog.update_status(status_text)
                    if found_count >= 0:
                        progress_text = (
                            f"📊 Found: {found_count}/{total_target} videos | "
                            f"API calls: {self.search_engine.api_client.api_call_count}/100"
                        )
                        self.progress_dialog.update_progress_info(progress_text)
                        progress_percentage = min((self.search_engine.api_client.api_call_count / 100) * 100, 100)
                        self.progress_dialog.update_progress_bar(progress_percentage)

            self.root.after(100, lambda: self._do_search_async(
                query, desired_count, published_after, min_vph, max_duration, progress_callback
            ))
        except Exception as e:
            self.logger.error(f"Search setup error: {e}")
            self._finish_search([], error=str(e))

    def _do_search_async(self, query: str, desired_count: int, published_after,
                         min_vph: float, max_duration, progress_callback):
        try:
            results = self.search_engine.smart_search_fill(
                query, desired_count, published_after, min_vph, max_duration, progress_callback
            )
            self._finish_search(results)
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            self._finish_search([], error=str(e))

    def _finish_search(self, results, error=None):
        self.current_search_active = False
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        active_tab = self.tab_manager.get_active_tab()
        if not active_tab: return

        try:
            if error:
                self.tab_manager.update_tab_status(active_tab.tab_id, "Error", 'error')
                messagebox.showerror("❌ Search Error", f"Error during search: {error}")
                return

            for video in results:
                self.tab_manager.add_result_to_tab(active_tab.tab_id, video)

            api_calls = self.search_engine.api_client.api_call_count
            if self.search_engine.api_client.search_cancelled:
                self.tab_manager.update_tab_status(active_tab.tab_id, f"{len(results)} partial", 'error')
                messagebox.showwarning(
                    "⚠️ Search Cancelled",
                    f"Search stopped. Found {len(results)} videos using {api_calls} API calls"
                )
            else:
                self.tab_manager.update_tab_status(active_tab.tab_id, f"{len(results)} results", 'complete')
                messagebox.showinfo(
                    "✅ Search Complete",
                    f"Found {len(results)} videos using {api_calls} API calls"
                )

            self.tab_counter_label.config(text=f"Tabs: {self.tab_manager.get_tab_count()}")
        except Exception as e:
            self.logger.error(f"Error finishing search: {e}")
            self.tab_manager.update_tab_status(active_tab.tab_id, "Error", 'error')

    def _cancel_search(self):
        self.search_engine.cancel_search()
        if self.progress_dialog:
            self.progress_dialog.update_status("🛑 Cancelling search...")

    def _get_published_after(self) -> Optional[datetime]:
        v = self.date_combo.get()
        if v == 'Any': return None
        now = datetime.now(timezone.utc)
        return now - (timedelta(days=1) if v == '24h'
                      else timedelta(days=2) if v == '2d'
                      else timedelta(days=7) if v == '7d'
                      else timedelta(0))

    def _preview_video(self):
        video = self.tab_manager.get_selected_video()
        if not video:
            messagebox.showinfo('Preview', 'Please select a video first.')
            return
        video_id = video.get('video_id')
        if video_id:
            url = f'https://www.youtube.com/embed/{video_id}'
            try:
                webview.create_window('Preview', url, width=800, height=450)
                webview.start()
            except Exception as e:
                self.logger.error(f"Preview error: {e}")
                messagebox.showerror('Preview Error', f'Could not open preview: {e}')

    def _download_video(self):
        video = self.tab_manager.get_selected_video()
        if not video:
            messagebox.showinfo('Download', 'Please select a video first.')
            return
        try:
            video_id = video.get('video_id')
            title = video.get('title', 'Unknown')
            url = f'https://www.youtube.com/watch?v={video_id}'
            query = self.query_entry.get().strip() or "default"
            output_path = self.media_processor.get_output_path(query)
            success = self.media_processor.download_video(video_id, url, output_path)
            if success:
                messagebox.showinfo('Download', f'Download started!\nSaved to:\n{output_path}')
                try: os.startfile(str(output_path))
                except Exception: pass
                try:
                    clean_title = title.replace('🟢 ','').replace('🔴 ','').strip()
                    caption, hashtags = VideoAnalyzer.generate_caption_and_hashtags(clean_title)
                    CaptionDialog(self.root, clean_title, caption, hashtags, str(output_path))
                except Exception as e:
                    self.logger.error(f'Caption generation error: {e}')
            else:
                messagebox.showerror('Download Error', 'Failed to download video')
        except Exception as e:
            self.logger.error(f'Download error: {e}')
            messagebox.showerror('Download Error', f'Error: {e}')

    def _transcribe_video(self):
        video = self.tab_manager.get_selected_video()
        if not video:
            messagebox.showinfo('Transcribe', 'Please select a video first.')
            return
        try:
            video_id = video.get('video_id')
            title = video.get('title', 'Unknown')
            url = f'https://www.youtube.com/watch?v={video_id}'
            progress = ProgressDialog(self.root, "Transcribing...")
            def progress_callback(status): progress.update_status(status)
            from config import AUDIO_CLIPS_PATH
            audio_path = self.media_processor.download_audio_only(video_id, url, AUDIO_CLIPS_PATH)
            if not audio_path:
                progress.close(); messagebox.showerror('Error', 'Failed to download audio'); return
            transcript = self.media_processor.transcribe_audio(audio_path, progress_callback)
            progress.close()
            if transcript:
                clean_title = title.replace('🟢 ','').replace('🔴 ','').strip()
                TranscriptDialog(self.root, clean_title, video_id, transcript)
                try:
                    caption, hashtags = VideoAnalyzer.generate_caption_and_hashtags(clean_title, transcript)
                    CaptionDialog(self.root, clean_title, caption, hashtags, str(AUDIO_CLIPS_PATH))
                except Exception as e:
                    self.logger.error(f'Caption generation error: {e}')
            else:
                messagebox.showerror('Error', 'Failed to transcribe audio')
        except Exception as e:
            if 'progress' in locals(): progress.close()
            self.logger.error(f'Transcription error: {e}')
            messagebox.showerror('Transcription Error', f'Error: {e}')

    def _find_raw_source(self):
        video = self.tab_manager.get_selected_video()
        if not video:
            messagebox.showinfo('Find Raw', 'Please select a video first.')
            return
        try:
            video_id = video.get('video_id')
            url = f'https://www.youtube.com/watch?v={video_id}'
            query = self.query_entry.get().strip() or "default"
            base_path = self.media_processor.get_output_path(query)
            progress = ProgressDialog(self.root, "Processing Video...")
            def progress_callback(status): progress.update_status(status)
            results = self.media_processor.process_video_for_analysis(
                video_id, url, base_path, progress_callback
            )
            progress.close()
            if results['success']:
                output_dir = base_path / video_id
                try: os.startfile(str(output_dir))
                except Exception: pass
                messagebox.showinfo(
                    'Find Raw',
                    'Frames & audio extracted.\nOpen the folder and drop a few clear frames into Google Lens/Bing/Yandex, or fingerprint the audio.\n\n'
                    f'Folder:\n{output_dir}'
                )
            else:
                messagebox.showerror('Error', 'Failed to process video')
        except Exception as e:
            if 'progress' in locals(): progress.close()
            self.logger.error(f'Raw source error: {e}')
            messagebox.showerror('Error', f'Error: {e}')

    def _open_clip_folder(self):
        try:
            desktop = Path.home() / 'Desktop'
            os.startfile(str(desktop))
        except Exception as e:
            messagebox.showerror('Error', f'Could not open folder:\n{e}')

    def _set_timer(self):
        time_str = simpledialog.askstring('Set Hustle Timer', 'Enter end time (e.g., 15:00 for 3:00 PM):')
        if not time_str: return
        try:
            hours, minutes = map(int, time_str.split(':'))
            now = datetime.now()
            target = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            if target < now: target += timedelta(days=1)
            self.timer_widget.set_timer(target)
        except Exception:
            messagebox.showerror('Timer Error', 'Invalid time format. Use HH:MM (24-hour format).')
