"""
RegDelta Extractor Agent
Rule-based obligation extraction using lexicon patterns
"""

import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Obligation:
    """Represents an extracted obligation"""
    section_id: str
    text: str
    severity: str  # 'high', 'medium', 'low'
    citations: List[str]
    modal_phrases: List[str]
    has_deadline: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'section_id': self.section_id,
            'text': self.text,
            'severity': self.severity,
            'citations': self.citations,
            'modal_phrases': self.modal_phrases,
            'has_deadline': self.has_deadline
        }


class ExtractorAgent:
    """Rule-based obligation extractor"""
    
    def __init__(self, lexicon_file: Path):
        self.lexicon = self._load_lexicon(lexicon_file)
        self.modal_patterns = self._compile_modal_patterns()
        self.severity_patterns = self._compile_severity_patterns()
        self.deadline_patterns = self._compile_deadline_patterns()
        self.stop_patterns = self._compile_stop_patterns()
        
        logger.info(f"ExtractorAgent initialized with {len(self.modal_patterns)} modal patterns")
    
    def _load_lexicon(self, lexicon_file: Path) -> Dict[str, Any]:
        """Load lexicon from YAML"""
        if not lexicon_file.exists():
            raise FileNotFoundError(f"Lexicon file not found: {lexicon_file}")
        
        with open(lexicon_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _compile_modal_patterns(self) -> List[tuple[str, re.Pattern]]:
        """Compile modal phrase patterns"""
        patterns = []
        
        for category, phrases in self.lexicon.get('modal_phrases', {}).items():
            for phrase in phrases:
                # Case-insensitive word boundary matching
                pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
                patterns.append((phrase, pattern))
        
        return patterns
    
    def _compile_severity_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile severity keyword patterns"""
        patterns = {}
        
        for severity, keywords in self.lexicon.get('severity_keywords', {}).items():
            patterns[severity] = [
                re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
                for kw in keywords
            ]
        
        return patterns
    
    def _compile_deadline_patterns(self) -> List[re.Pattern]:
        """Compile deadline detection patterns"""
        patterns = []
        
        for pattern_str in self.lexicon.get('deadline_patterns', []):
            patterns.append(re.compile(pattern_str, re.IGNORECASE))
        
        return patterns
    
    def _compile_stop_patterns(self) -> List[re.Pattern]:
        """Compile stop phrase patterns"""
        patterns = []
        
        for phrase in self.lexicon.get('stop_phrases', []):
            patterns.append(re.compile(phrase, re.IGNORECASE))
        
        return patterns
    
    def _is_stop_phrase(self, text: str) -> bool:
        """Check if text matches stop phrases (should be excluded)"""
        for pattern in self.stop_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _detect_modal_phrases(self, text: str) -> List[str]:
        """Detect modal phrases in text"""
        found_phrases = []
        
        for phrase, pattern in self.modal_patterns:
            if pattern.search(text):
                found_phrases.append(phrase)
        
        return found_phrases
    
    def _has_deadline(self, text: str) -> bool:
        """Check if text contains deadline patterns"""
        for pattern in self.deadline_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _determine_severity(self, text: str, modal_phrases: List[str], has_deadline: bool) -> str:
        """
        Determine obligation severity based on keywords and context
        
        Severity logic:
        - High: Contains high-severity keywords, prohibitions, or time-critical requirements
        - Medium: Contains mandatory keywords (must/shall/required)
        - Low: Contains recommended keywords (should/advised)
        """
        text_lower = text.lower()
        
        # Check high severity keywords
        for pattern in self.severity_patterns.get('high', []):
            if pattern.search(text):
                return 'high'
        
        # Check if it's a prohibition (must not, shall not, etc.)
        prohibition_phrases = self.lexicon.get('modal_phrases', {}).get('prohibitions', [])
        for phrase in prohibition_phrases:
            if phrase.lower() in text_lower:
                return 'high'
        
        # Time-bound requirements get boosted severity
        if has_deadline:
            # Check medium severity keywords
            for pattern in self.severity_patterns.get('medium', []):
                if pattern.search(text):
                    return 'high'  # Boost to high if deadline + mandatory
        
        # Check medium severity keywords
        for pattern in self.severity_patterns.get('medium', []):
            if pattern.search(text):
                return 'medium'
        
        # Check if mandatory modal phrases present
        mandatory_phrases = self.lexicon.get('modal_phrases', {}).get('mandatory', [])
        for phrase in mandatory_phrases:
            if phrase.lower() in text_lower:
                return 'medium'
        
        # Default to low for recommendations
        return 'low'
    
    def extract_obligations(self, 
                          section_text: str, 
                          section_id: str,
                          min_length: int = 30) -> List[Obligation]:
        """
        Extract obligations from a section of text
        
        Args:
            section_text: Text to analyze
            section_id: Identifier for this section
            min_length: Minimum text length to consider (filters out headers)
        
        Returns:
            List of extracted obligations
        """
        obligations = []
        
        # Skip if too short or is stop phrase
        if len(section_text) < min_length or self._is_stop_phrase(section_text):
            return obligations
        
        # Detect modal phrases
        modal_phrases = self._detect_modal_phrases(section_text)
        
        # If no modal phrases found, not an obligation
        if not modal_phrases:
            return obligations
        
        # Check for deadline
        has_deadline = self._has_deadline(section_text)
        
        # Determine severity
        severity = self._determine_severity(section_text, modal_phrases, has_deadline)
        
        # Extract citations (simple regex for common patterns)
        citations = self._extract_citations(section_text)
        
        # Create obligation
        obligation = Obligation(
            section_id=section_id,
            text=section_text,
            severity=severity,
            citations=citations,
            modal_phrases=modal_phrases,
            has_deadline=has_deadline
        )
        
        obligations.append(obligation)
        logger.debug(f"Extracted {severity} obligation from section {section_id}")
        
        return obligations
    
    def _extract_citations(self, text: str) -> List[str]:
        """Extract citation references from text"""
        citations = []
        
        # Common citation patterns
        patterns = [
            r'Section\s+\d+(?:\.\d+)*',
            r'Article\s+\d+(?:\.\d+)*',
            r'Clause\s+\d+(?:\.\d+)*',
            r'Paragraph\s+\d+(?:\.\d+)*',
            r'Regulation\s+\d+(?:\.\d+)*',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            citations.extend(matches)
        
        return list(set(citations))  # Remove duplicates
    
    def extract_from_paragraphs(self, paragraphs: List[str]) -> List[Obligation]:
        """
        Extract obligations from a list of paragraphs
        
        Args:
            paragraphs: List of paragraph texts
        
        Returns:
            List of all extracted obligations
        """
        all_obligations = []
        
        for idx, para in enumerate(paragraphs):
            section_id = f"para_{idx}"
            obligations = self.extract_obligations(para, section_id)
            all_obligations.extend(obligations)
        
        logger.info(f"Extracted {len(all_obligations)} obligations from {len(paragraphs)} paragraphs")
        return all_obligations
    
    def get_extraction_stats(self, obligations: List[Obligation]) -> Dict[str, Any]:
        """Get statistics about extracted obligations"""
        if not obligations:
            return {
                'total': 0,
                'by_severity': {'high': 0, 'medium': 0, 'low': 0},
                'with_deadlines': 0,
                'with_citations': 0
            }
        
        stats = {
            'total': len(obligations),
            'by_severity': {
                'high': sum(1 for o in obligations if o.severity == 'high'),
                'medium': sum(1 for o in obligations if o.severity == 'medium'),
                'low': sum(1 for o in obligations if o.severity == 'low')
            },
            'with_deadlines': sum(1 for o in obligations if o.has_deadline),
            'with_citations': sum(1 for o in obligations if o.citations)
        }
        
        return stats


def create_extractor(lexicon_file: Optional[Path] = None) -> ExtractorAgent:
    """Create extractor agent instance"""
    if lexicon_file is None:
        lexicon_file = Path("lexicon.yml")
    
    return ExtractorAgent(lexicon_file)
