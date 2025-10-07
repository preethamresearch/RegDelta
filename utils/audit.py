"""
RegDelta Audit Logger
Tamper-evident append-only audit trail with SHA-256 hash chain
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import threading

logger = logging.getLogger(__name__)


def convert_to_serializable(obj):
    """Recursively convert numpy types to Python native types"""
    try:
        import numpy as np
        
        if isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: convert_to_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(convert_to_serializable(item) for item in obj)
        else:
            return obj
    except ImportError:
        # If numpy not available, just return the object
        if isinstance(obj, dict):
            return {key: convert_to_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(convert_to_serializable(item) for item in obj)
        else:
            return obj


class AuditLogger:
    """Append-only audit logger with hash chain for tamper evidence"""
    
    def __init__(self, audit_file: Path):
        self.audit_file = audit_file
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()  # Thread-safe writes
        
        # Create file if it doesn't exist
        if not self.audit_file.exists():
            self.audit_file.touch()
            logger.info(f"Created new audit log: {self.audit_file}")
        
        self.last_hash = self._get_last_hash()
    
    def _get_last_hash(self) -> str:
        """Get the last hash from the audit log"""
        if self.audit_file.stat().st_size == 0:
            return "0" * 64  # Genesis hash
        
        # Read last line
        with open(self.audit_file, 'rb') as f:
            try:
                # Move to end and read backwards to find last line
                f.seek(-2, 2)  # Skip final newline
                while f.read(1) != b'\n':
                    f.seek(-2, 1)
                last_line = f.readline().decode('utf-8')
                
                entry = json.loads(last_line)
                return entry.get('sha256', "0" * 64)
            except (OSError, json.JSONDecodeError):
                # Empty file or corrupted
                return "0" * 64
    
    def _compute_hash(self, entry: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of entry including previous hash"""
        # Create deterministic string representation
        data = {
            'ts': entry['ts'],
            'actor': entry['actor'],
            'action': entry['action'],
            'payload': convert_to_serializable(entry['payload']),
            'prev_sha256': entry['prev_sha256']
        }
        
        data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
    
    def log(self, actor: str, action: str, payload: Dict[str, Any]) -> str:
        """
        Log an audit entry (thread-safe)
        
        Args:
            actor: Who performed the action (user, agent, system)
            action: What action was performed
            payload: Additional context/data
        
        Returns:
            SHA-256 hash of the logged entry
        """
        with self._lock:  # Ensure atomic read-modify-write
            # Convert payload to serializable format
            serializable_payload = convert_to_serializable(payload)
            
            # Use the in-memory last_hash (already updated from previous write)
            entry = {
                'ts': datetime.utcnow().isoformat() + 'Z',
                'actor': actor,
                'action': action,
                'payload': serializable_payload,
                'prev_sha256': self.last_hash
            }
            
            # Compute hash
            entry['sha256'] = self._compute_hash(entry)
            
            # Append to file with flush
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, separators=(',', ':')) + '\n')
                f.flush()  # Force flush to disk
            
            # Update last hash
            self.last_hash = entry['sha256']
            
            logger.debug(f"Audit log: {action} by {actor}")
            return entry['sha256']
    
    def verify_chain(self) -> tuple[bool, Optional[int]]:
        """
        Verify the integrity of the hash chain
        
        Returns:
            (is_valid, first_invalid_line_number)
        """
        if self.audit_file.stat().st_size == 0:
            return True, None
        
        prev_hash = "0" * 64
        line_num = 0
        
        with open(self.audit_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_num += 1
                try:
                    entry = json.loads(line)
                    
                    # Check previous hash matches
                    if entry['prev_sha256'] != prev_hash:
                        logger.error(f"Hash chain broken at line {line_num}: prev_hash mismatch")
                        return False, line_num
                    
                    # Verify hash
                    expected_hash = self._compute_hash(entry)
                    if entry['sha256'] != expected_hash:
                        logger.error(f"Hash chain broken at line {line_num}: hash mismatch")
                        return False, line_num
                    
                    prev_hash = entry['sha256']
                    
                except json.JSONDecodeError:
                    logger.error(f"Hash chain broken at line {line_num}: invalid JSON")
                    return False, line_num
        
        logger.info(f"Audit chain verified: {line_num} entries OK")
        return True, None
    
    def get_entries(self, 
                    action_filter: Optional[str] = None,
                    actor_filter: Optional[str] = None,
                    limit: Optional[int] = None) -> list[Dict[str, Any]]:
        """
        Retrieve audit entries with optional filtering
        
        Args:
            action_filter: Filter by action type
            actor_filter: Filter by actor
            limit: Maximum number of entries to return (most recent)
        
        Returns:
            List of audit entries
        """
        entries = []
        
        if self.audit_file.stat().st_size == 0:
            return entries
        
        with open(self.audit_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    
                    # Apply filters
                    if action_filter and entry['action'] != action_filter:
                        continue
                    if actor_filter and entry['actor'] != actor_filter:
                        continue
                    
                    entries.append(entry)
                    
                except json.JSONDecodeError:
                    continue
        
        # Return most recent if limit specified
        if limit:
            entries = entries[-limit:]
        
        return entries
    
    def export_audit_trail(self, output_file: Path):
        """Export full audit trail to a separate file"""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.audit_file, 'r', encoding='utf-8') as src:
            with open(output_file, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        
        logger.info(f"Exported audit trail to {output_file}")


# Singleton instance
_audit_logger_instance = None

def get_audit_logger(audit_file: Optional[Path] = None) -> AuditLogger:
    """Get or create audit logger instance (singleton)"""
    global _audit_logger_instance
    
    if _audit_logger_instance is None:
        if audit_file is None:
            from utils.config import get_config
            config = get_config()
            audit_file = config.audit_dir / "audit.jsonl"
        
        _audit_logger_instance = AuditLogger(audit_file)
    
    return _audit_logger_instance
