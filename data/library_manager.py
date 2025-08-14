"""
Library items management system
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from utils.logging import log_upgrade

@dataclass
class LibraryItem:
    """Data class for a library item"""
    video_id: str
    title: str
    display_title: str
    viral_score: float
    views: int
    likes: int
    ratio: float
    vph: float
    duration: str
    age: str
    repost_flag: bool
    repost_reason: str
    date_saved: str
    folder: str = "Default"
    notes: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'LibraryItem':
        """Create from dictionary"""
        title = data.get('title', '')
        return cls(
            video_id=data.get('video_id', ''),
            title=title,
            display_title=data.get('display_title', title),
            viral_score=data.get('viral_score', 0.0),
            views=data.get('views', 0),
            likes=data.get('likes', 0),
            ratio=data.get('ratio', 0.0),
            vph=data.get('vph', 0.0),
            duration=data.get('duration', '00:00'),
            age=data.get('age', ''),
            repost_flag=data.get('repost_flag', False),
            repost_reason=data.get('repost_reason', ''),
            date_saved=data.get('date_saved', ''),
            folder=data.get('folder', 'Default'),
            notes=data.get('notes', '')
        )

class LibraryManager:
    """Manages library items and folders"""

    def __init__(self, library_file: str = 'library.json'):
        self.library_file = library_file
        self.items: List[LibraryItem] = []
        self.folders: List[str] = ["Default"]
        self.load_library()

    def load_library(self) -> bool:
        """Load library items from file"""
        if not os.path.exists(self.library_file):
            return True

        try:
            with open(self.library_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load items
            items_data = data.get('items', [])
            self.items = [LibraryItem.from_dict(w) for w in items_data]

            # Load folders
            self.folders = data.get('folders', ["Default"])
            if "Default" not in self.folders:
                self.folders.insert(0, "Default")

            log_upgrade(f"Loaded {len(self.items)} library items in {len(self.folders)} folders")
            return True

        except Exception as e:
            log_upgrade(f"Error loading library: {e}")
            return False

    def save_library(self) -> bool:
        """Save library items to file"""
        try:
            data = {
                'items': [item.to_dict() for item in self.items],
                'folders': self.folders,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.library_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            log_upgrade(f"Saved {len(self.items)} library items")
            return True

        except Exception as e:
            log_upgrade(f"Error saving library items: {e}")
            return False

    def add_item(self, video_data: Dict, folder: str = "Default", notes: str = "") -> bool:
        """Add a video to the library"""
        video_id = video_data.get('video_id', '')

        # Check if already exists
        if self.get_item_by_id(video_id):
            return False  # Already exists

        title = video_data.get('title', '')
        item = LibraryItem(
            video_id=video_id,
            title=title,
            display_title=title,
            viral_score=video_data.get('viral_score', 0.0),
            views=video_data.get('views', 0),
            likes=video_data.get('likes', 0),
            ratio=video_data.get('ratio', 0.0),
            vph=video_data.get('vph', 0.0),
            duration=video_data.get('duration', '00:00'),
            age=video_data.get('age', ''),
            repost_flag=video_data.get('repost_flag', False),
            repost_reason=video_data.get('repost_reason', ''),
            date_saved=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            folder=folder,
            notes=notes
        )

        self.items.append(item)
        return self.save_library()

    def remove_item(self, video_id: str) -> bool:
        """Remove a library item by video ID"""
        original_count = len(self.items)
        self.items = [w for w in self.items if w.video_id != video_id]

        if len(self.items) < original_count:
            return self.save_library()
        return False

    def get_item_by_id(self, video_id: str) -> Optional[LibraryItem]:
        """Get library item by video ID"""
        for item in self.items:
            if item.video_id == video_id:
                return item
        return None

    def get_items_by_folder(self, folder: str) -> List[LibraryItem]:
        """Get all items in a specific folder"""
        return [w for w in self.items if w.folder == folder]

    def move_item_to_folder(self, video_id: str, new_folder: str) -> bool:
        """Move item to a different folder"""
        if new_folder not in self.folders:
            return False

        item = self.get_item_by_id(video_id)
        if item:
            item.folder = new_folder
            return self.save_library()
        return False

    def add_folder(self, folder_name: str) -> bool:
        """Add a new folder"""
        if folder_name and folder_name not in self.folders:
            self.folders.append(folder_name)
            return self.save_library()
        return False

    def remove_folder(self, folder_name: str) -> bool:
        """Remove a folder (moves items to Default)"""
        if folder_name == "Default" or folder_name not in self.folders:
            return False

        # Move all items in this folder to Default
        for item in self.items:
            if item.folder == folder_name:
                item.folder = "Default"

        self.folders.remove(folder_name)
        return self.save_library()

    def rename_folder(self, old_name: str, new_name: str) -> bool:
        """Rename a folder"""
        if old_name not in self.folders or new_name in self.folders or not new_name:
            return False

        # Update folder name in items
        for item in self.items:
            if item.folder == old_name:
                item.folder = new_name

        # Update folder list
        folder_index = self.folders.index(old_name)
        self.folders[folder_index] = new_name

        return self.save_library()

    def rename_item(self, video_id: str, new_display_title: str) -> bool:
        """Renames the display title of a library item."""
        item = self.get_item_by_id(video_id)
        if item and new_display_title:
            item.display_title = new_display_title.strip()
            return self.save_library()
        return False

    def get_all_folders(self) -> List[str]:
        """Get all folder names"""
        return self.folders.copy()

    def get_item_count(self) -> int:
        """Get total number of library items"""
        return len(self.items)

    def get_folder_count(self, folder: str) -> int:
        """Get number of items in a folder"""
        return len(self.get_items_by_folder(folder))

    def update_item_notes(self, video_id: str, notes: str) -> bool:
        """Update notes for a library item"""
        item = self.get_item_by_id(video_id)
        if item:
            item.notes = notes
            return self.save_library()
        return False

    def search_items(self, query: str) -> List[LibraryItem]:
        """Search library items by title"""
        query_lower = query.lower()
        return [
            w for w in self.items
            if query_lower in w.title.lower() or query_lower in w.notes.lower()
        ]