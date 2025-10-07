"""
RegDelta Diff Engine
Paragraph-level document diffing with opcodes
"""

import difflib
from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DiffOp:
    """Represents a single diff operation"""
    op: str  # 'equal', 'insert', 'delete', 'replace'
    old_start: int
    old_end: int
    new_start: int
    new_end: int
    old_text: List[str]
    new_text: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'op': self.op,
            'old_range': [self.old_start, self.old_end],
            'new_range': [self.new_start, self.new_end],
            'old_text': self.old_text,
            'new_text': self.new_text,
            'summary': self._get_summary()
        }
    
    def _get_summary(self) -> str:
        """Generate human-readable summary"""
        if self.op == 'equal':
            return f"Unchanged: {len(self.old_text)} paragraphs"
        elif self.op == 'insert':
            return f"Added: {len(self.new_text)} paragraphs"
        elif self.op == 'delete':
            return f"Removed: {len(self.old_text)} paragraphs"
        elif self.op == 'replace':
            return f"Modified: {len(self.old_text)} → {len(self.new_text)} paragraphs"
        return "Unknown"


class DocumentDiff:
    """Paragraph-level document differ"""
    
    def __init__(self, old_paragraphs: List[str], new_paragraphs: List[str]):
        self.old_paragraphs = old_paragraphs
        self.new_paragraphs = new_paragraphs
        self.ops: List[DiffOp] = []
        self._compute_diff()
    
    def _compute_diff(self):
        """Compute diff operations using SequenceMatcher"""
        matcher = difflib.SequenceMatcher(
            None,
            self.old_paragraphs,
            self.new_paragraphs,
            autojunk=False
        )
        
        for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            op = DiffOp(
                op=tag,
                old_start=old_start,
                old_end=old_end,
                new_start=new_start,
                new_end=new_end,
                old_text=self.old_paragraphs[old_start:old_end],
                new_text=self.new_paragraphs[new_start:new_end]
            )
            self.ops.append(op)
        
        logger.info(f"Computed diff: {len(self.ops)} operations")
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary counts of diff operations"""
        summary = {
            'equal': 0,
            'insert': 0,
            'delete': 0,
            'replace': 0,
            'total_ops': len(self.ops)
        }
        
        for op in self.ops:
            summary[op.op] += 1
        
        # Calculate paragraphs affected
        summary['paragraphs_added'] = sum(
            len(op.new_text) for op in self.ops if op.op in ['insert', 'replace']
        )
        summary['paragraphs_removed'] = sum(
            len(op.old_text) for op in self.ops if op.op in ['delete', 'replace']
        )
        summary['paragraphs_unchanged'] = sum(
            len(op.old_text) for op in self.ops if op.op == 'equal'
        )
        
        return summary
    
    def get_changed_sections(self) -> List[DiffOp]:
        """Get only the changed sections (exclude 'equal')"""
        return [op for op in self.ops if op.op != 'equal']
    
    def get_changes_with_context(self, context_lines: int = 2) -> List[Dict[str, Any]]:
        """
        Get changed sections with surrounding context
        
        Args:
            context_lines: Number of unchanged paragraphs to include before/after changes
        
        Returns:
            List of change blocks with context
        """
        changes = []
        
        for i, op in enumerate(self.ops):
            if op.op == 'equal':
                continue
            
            # Find context before
            context_before = []
            for j in range(i - 1, -1, -1):
                if self.ops[j].op == 'equal':
                    context_before = self.ops[j].old_text[-context_lines:]
                    break
            
            # Find context after
            context_after = []
            for j in range(i + 1, len(self.ops)):
                if self.ops[j].op == 'equal':
                    context_after = self.ops[j].old_text[:context_lines]
                    break
            
            changes.append({
                'op': op.op,
                'context_before': context_before,
                'old_text': op.old_text,
                'new_text': op.new_text,
                'context_after': context_after,
                'position': {
                    'old': [op.old_start, op.old_end],
                    'new': [op.new_start, op.new_end]
                }
            })
        
        return changes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entire diff to dictionary"""
        return {
            'summary': self.get_summary(),
            'operations': [op.to_dict() for op in self.ops],
            'changed_sections': [op.to_dict() for op in self.get_changed_sections()]
        }
    
    def get_unified_diff(self, old_label: str = "baseline", new_label: str = "new") -> str:
        """
        Generate unified diff format (similar to git diff)
        
        Args:
            old_label: Label for old/baseline version
            new_label: Label for new version
        
        Returns:
            Unified diff string
        """
        diff_lines = []
        
        for op in self.ops:
            if op.op == 'equal':
                continue
            
            diff_lines.append(f"\n{'=' * 60}")
            diff_lines.append(f"Change: {op.op.upper()}")
            diff_lines.append(f"Position: Old[{op.old_start}:{op.old_end}] → New[{op.new_start}:{op.new_end}]")
            diff_lines.append('=' * 60)
            
            if op.old_text:
                diff_lines.append(f"\n--- {old_label}")
                for i, line in enumerate(op.old_text, start=op.old_start):
                    diff_lines.append(f"- [{i}] {line[:200]}...")
            
            if op.new_text:
                diff_lines.append(f"\n+++ {new_label}")
                for i, line in enumerate(op.new_text, start=op.new_start):
                    diff_lines.append(f"+ [{i}] {line[:200]}...")
        
        return '\n'.join(diff_lines)


def diff(old_paragraphs: List[str], new_paragraphs: List[str]) -> DocumentDiff:
    """
    Compute paragraph-level diff between two documents
    
    Args:
        old_paragraphs: Baseline document paragraphs
        new_paragraphs: New document paragraphs
    
    Returns:
        DocumentDiff object with operations and summary
    """
    return DocumentDiff(old_paragraphs, new_paragraphs)


def quick_diff_summary(old_paragraphs: List[str], new_paragraphs: List[str]) -> Dict[str, int]:
    """Quick diff summary without storing all operations"""
    doc_diff = diff(old_paragraphs, new_paragraphs)
    return doc_diff.get_summary()
