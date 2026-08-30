"""Rerere (Reuse Recorded Resolution) - automatic conflict resolution.

When the same conflict appears again, vesi will automatically apply
the previously recorded resolution. This is one of Git's most powerful
features for collaborative work.

How it works:
1. When you resolve a conflict, vesi records the conflict + resolution
2. When the same conflict appears again, vesi offers to apply the saved resolution
3. You can also manually list, forget, or diff recorded resolutions
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RerereRecord:
    """A recorded conflict resolution."""
    conflict_hash: str  # Hash of the conflict markers
    resolution_hash: str  # Hash of the resolved content
    filepath: str  # File path
    conflict_content: str  # Original conflict markers
    resolution_content: str  # How it was resolved
    timestamp: float  # When recorded
    branch_context: str = ""  # Optional branch info
    
    @property
    def age_hours(self) -> float:
        return (time.time() - self.timestamp) / 3600
    
    @property
    def age_days(self) -> float:
        return self.age_hours / 24
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_hash": self.conflict_hash,
            "resolution_hash": self.resolution_hash,
            "filepath": self.filepath,
            "conflict_content": self.conflict_content,
            "resolution_content": self.resolution_content,
            "timestamp": self.timestamp,
            "branch_context": self.branch_context,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RerereRecord:
        return cls(
            conflict_hash=data["conflict_hash"],
            resolution_hash=data["resolution_hash"],
            filepath=data["filepath"],
            conflict_content=data["conflict_content"],
            resolution_content=data["resolution_content"],
            timestamp=data["timestamp"],
            branch_context=data.get("branch_context", ""),
        )


class RerereManager:
    """Manages conflict resolution records.
    
    Stores resolutions in .vesi/rerere/ directory:
    - .vesi/rerere/records.json  — index of all records
    - .vesi/rerere/<hash>.json   — individual records
    """
    
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.rerere_dir = repo_root / ".vesi" / "rerere"
        self.records_file = self.rerere_dir / "records.json"
    
    def _ensure_dir(self) -> None:
        self.rerere_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_index(self) -> dict[str, str]:
        """Load conflict_hash -> record_file mapping."""
        if not self.records_file.is_file():
            return {}
        try:
            return json.loads(self.records_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    
    def _save_index(self, index: dict[str, str]) -> None:
        self._ensure_dir()
        self.records_file.write_text(
            json.dumps(index, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    
    def _hash_content(self, content: str) -> str:
        """Hash conflict content for matching."""
        # Normalize whitespace for better matching
        normalized = "\n".join(
            line.rstrip() for line in content.split("\n")
        )
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def record_resolution(
        self,
        filepath: str,
        conflict_content: str,
        resolution_content: str,
        branch_context: str = "",
    ) -> str:
        """Record a conflict resolution.
        
        Args:
            filepath: Path to the conflicted file
            conflict_content: The file content with conflict markers
            resolution_content: The resolved file content
            branch_context: Optional branch name for context
        
        Returns:
            The conflict hash for later lookup
        """
        self._ensure_dir()
        
        conflict_hash = self._hash_content(conflict_content)
        resolution_hash = self._hash_content(resolution_content)
        
        record = RerereRecord(
            conflict_hash=conflict_hash,
            resolution_hash=resolution_hash,
            filepath=filepath,
            conflict_content=conflict_content,
            resolution_content=resolution_content,
            timestamp=time.time(),
            branch_context=branch_context,
        )
        
        # Save individual record
        record_file = self.rerere_dir / f"{conflict_hash}.json"
        record_file.write_text(
            json.dumps(record.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        
        # Update index
        index = self._load_index()
        index[conflict_hash] = f"{conflict_hash}.json"
        self._save_index(index)
        
        return conflict_hash
    
    def find_resolution(
        self,
        filepath: str,
        conflict_content: str,
    ) -> RerereRecord | None:
        """Find a matching resolution for a conflict.
        
        Args:
            filepath: Path to the conflicted file
            conflict_content: The file content with conflict markers
        
        Returns:
            Matching RerereRecord or None
        """
        conflict_hash = self._hash_content(conflict_content)
        index = self._load_index()
        
        if conflict_hash in index:
            record_file = self.rerere_dir / index[conflict_hash]
            if record_file.is_file():
                try:
                    data = json.loads(record_file.read_text(encoding="utf-8"))
                    record = RerereRecord.from_dict(data)
                    
                    # Verify filepath matches
                    if record.filepath == filepath:
                        return record
                except (json.JSONDecodeError, OSError, KeyError):
                    pass
        
        return None
    
    def auto_resolve(
        self,
        filepath: str,
        conflict_content: str,
        dry_run: bool = False,
    ) -> tuple[bool, str]:
        """Try to auto-resolve a conflict using recorded resolution.
        
        Args:
            filepath: Path to the conflicted file
            conflict_content: Current conflict markers
            dry_run: If True, don't write, just report
        
        Returns:
            (success, message)
        """
        record = self.find_resolution(filepath, conflict_content)
        
        if not record:
            return False, "Tidak ada resolusi tersimpan untuk konflik ini"
        
        if not dry_run:
            file_path = self.repo_root / filepath
            file_path.write_text(record.resolution_content, encoding="utf-8")
        
        age = f"{record.age_days:.0f} hari" if record.age_days >= 1 else f"{record.age_hours:.0f} jam"
        return True, f"Resolusi diterapkan (direkam {age} lalu)"
    
    def list_records(
        self,
        filepath: str | None = None,
        max_age_days: int | None = None,
    ) -> list[RerereRecord]:
        """List recorded resolutions.
        
        Args:
            filepath: Filter by filepath
            max_age_days: Only include records newer than this
        """
        index = self._load_index()
        records = []
        
        for conflict_hash, filename in index.items():
            record_file = self.rerere_dir / filename
            if not record_file.is_file():
                continue
            
            try:
                data = json.loads(record_file.read_text(encoding="utf-8"))
                record = RerereRecord.from_dict(data)
                
                if filepath and record.filepath != filepath:
                    continue
                
                if max_age_days and record.age_days > max_age_days:
                    continue
                
                records.append(record)
            except (json.JSONDecodeError, OSError, KeyError):
                continue
        
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records
    
    def forget(
        self,
        filepath: str | None = None,
        conflict_hash: str | None = None,
    ) -> int:
        """Forget recorded resolutions.
        
        Args:
            filepath: Forget all resolutions for this file
            conflict_hash: Forget a specific resolution
        
        Returns:
            Number of records forgotten
        """
        index = self._load_index()
        forgotten = 0
        
        to_remove = []
        for hash_key, filename in index.items():
            record_file = self.rerere_dir / filename
            
            if conflict_hash and hash_key != conflict_hash:
                continue
            
            if filepath:
                try:
                    data = json.loads(record_file.read_text(encoding="utf-8"))
                    if data.get("filepath") != filepath:
                        continue
                except Exception:
                    continue
            
            # Remove the record file
            if record_file.is_file():
                record_file.unlink()
            
            to_remove.append(hash_key)
            forgotten += 1
        
        for key in to_remove:
            del index[key]
        
        self._save_index(index)
        return forgotten
    
    def get_diff(
        self,
        conflict_hash: str,
    ) -> tuple[str, str] | None:
        """Get conflict vs resolution diff.
        
        Returns:
            (conflict_content, resolution_content) or None
        """
        index = self._load_index()
        if conflict_hash not in index:
            return None
        
        record_file = self.rerere_dir / index[conflict_hash]
        if not record_file.is_file():
            return None
        
        try:
            data = json.loads(record_file.read_text(encoding="utf-8"))
            record = RerereRecord.from_dict(data)
            return record.conflict_content, record.resolution_content
        except Exception:
            return None
    
    def cleanup(self, max_age_days: int = 90) -> int:
        """Remove old records.
        
        Args:
            max_age_days: Remove records older than this
        
        Returns:
            Number of records removed
        """
        records = self.list_records(max_age_days=max_age_days)
        hashes_to_forget = [r.conflict_hash for r in records]
        
        forgotten = 0
        for h in hashes_to_forget:
            self.forget(conflict_hash=h)
            forgotten += 1
        
        return forgotten
    
    def stats(self) -> dict[str, Any]:
        """Get rerere statistics."""
        records = self.list_records()
        
        files = set()
        for r in records:
            files.add(r.filepath)
        
        return {
            "total_records": len(records),
            "unique_files": len(files),
            "oldest_record": min((r.age_days for r in records), default=0),
            "newest_record": max((r.age_days for r in records), default=0),
        }
