"""
RegDelta Mapper Agent
Control mapping using local embeddings (SentenceTransformers) + FAISS + fuzzy matching
"""

import numpy as np
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Control:
    """Represents a control from catalog"""
    control_id: str
    domain: str
    title: str
    description: str
    owner: str
    evidence_examples: List[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Control':
        """Create Control from dictionary"""
        return cls(
            control_id=data['control_id'],
            domain=data['domain'],
            title=data['title'],
            description=data['description'],
            owner=data['owner'],
            evidence_examples=data.get('evidence_examples', [])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'control_id': self.control_id,
            'domain': self.domain,
            'title': self.title,
            'description': self.description,
            'owner': self.owner,
            'evidence_examples': self.evidence_examples
        }
    
    def get_text_for_embedding(self) -> str:
        """Get combined text for embedding"""
        return f"{self.title}. {self.description}"


@dataclass
class ControlMapping:
    """Represents a mapping between obligation and control"""
    obligation_text: str
    control_id: str
    control_title: str
    score: float
    cosine_score: float
    lexical_score: float
    status: str = 'review'  # 'accepted', 'review', 'rejected'
    reviewer: Optional[str] = None
    comment: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'obligation_text': self.obligation_text[:200] + '...',
            'control_id': self.control_id,
            'control_title': self.control_title,
            'score': float(round(self.score, 3)),
            'cosine_score': float(round(self.cosine_score, 3)),
            'lexical_score': float(round(self.lexical_score, 3)),
            'status': self.status,
            'reviewer': self.reviewer,
            'comment': self.comment
        }


class MapperAgent:
    """Control mapper using local embeddings and fuzzy matching"""
    
    def __init__(self, 
                 catalog_dir: Path,
                 catalog_files: List[str],
                 cosine_weight: float = 0.7,
                 lexical_weight: float = 0.3):
        self.catalog_dir = catalog_dir
        self.cosine_weight = cosine_weight
        self.lexical_weight = lexical_weight
        
        # Load controls from catalogs
        self.controls: List[Control] = []
        self._load_catalogs(catalog_files)
        
        # Initialize embedding model and index
        self.model = None
        self.index = None
        self.control_embeddings = None
        
        logger.info(f"MapperAgent initialized with {len(self.controls)} controls")
    
    def _load_catalogs(self, catalog_files: List[str]):
        """Load control catalogs from YAML files"""
        for catalog_file in catalog_files:
            catalog_path = self.catalog_dir / catalog_file
            
            if not catalog_path.exists():
                logger.warning(f"Catalog file not found: {catalog_path}")
                continue
            
            with open(catalog_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            controls_data = data.get('controls', [])
            for control_data in controls_data:
                control = Control.from_dict(control_data)
                self.controls.append(control)
            
            logger.info(f"Loaded {len(controls_data)} controls from {catalog_file}")
    
    def build_index(self):
        """Build FAISS index with control embeddings"""
        try:
            from sentence_transformers import SentenceTransformer
            import faiss
        except ImportError as e:
            raise ImportError(
                "Missing dependencies. Install with: "
                "pip install sentence-transformers faiss-cpu"
            ) from e
        
        logger.info("Loading SentenceTransformer model (this may take a moment)...")
        
        # Use a lightweight model for local CPU inference
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get control texts for embedding
        control_texts = [ctrl.get_text_for_embedding() for ctrl in self.controls]
        
        logger.info(f"Encoding {len(control_texts)} control descriptions...")
        self.control_embeddings = self.model.encode(
            control_texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # Build FAISS index (using L2 distance, will convert to cosine)
        dimension = self.control_embeddings.shape[1]
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.control_embeddings)
        
        # Create index
        self.index = faiss.IndexFlatIP(dimension)  # Inner product = cosine after normalization
        self.index.add(self.control_embeddings)
        
        logger.info(f"Built FAISS index with {self.index.ntotal} vectors")
    
    def _compute_fuzzy_score(self, text1: str, text2: str) -> float:
        """Compute fuzzy token ratio similarity"""
        try:
            from rapidfuzz import fuzz
        except ImportError:
            logger.warning("rapidfuzz not installed, using simple token overlap")
            return self._simple_token_overlap(text1, text2)
        
        return fuzz.token_set_ratio(text1, text2) / 100.0
    
    def _simple_token_overlap(self, text1: str, text2: str) -> float:
        """Simple token overlap fallback if rapidfuzz not available"""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union)
    
    def search_controls(self, 
                       query_text: str, 
                       k: int = 5) -> List[Tuple[Control, float, float, float]]:
        """
        Search for matching controls
        
        Args:
            query_text: Obligation text to match
            k: Number of top results to return
        
        Returns:
            List of (Control, blended_score, cosine_score, lexical_score)
        """
        if self.index is None:
            raise RuntimeError("Index not built. Call build_index() first.")
        
        # Encode query
        query_embedding = self.model.encode([query_text], convert_to_numpy=True)
        
        # Normalize for cosine similarity
        import faiss
        faiss.normalize_L2(query_embedding)
        
        # Search FAISS index
        cosine_scores, indices = self.index.search(query_embedding, k)
        cosine_scores = cosine_scores[0]  # Unpack batch dimension
        indices = indices[0]
        
        # Compute blended scores
        results = []
        
        for idx, cosine_score in zip(indices, cosine_scores):
            if idx == -1:  # FAISS returns -1 for empty results
                continue
            
            control = self.controls[idx]
            control_text = control.get_text_for_embedding()
            
            # Compute lexical similarity
            lexical_score = self._compute_fuzzy_score(query_text, control_text)
            
            # Blend scores
            blended_score = (
                self.cosine_weight * cosine_score + 
                self.lexical_weight * lexical_score
            )
            
            results.append((control, blended_score, cosine_score, lexical_score))
        
        # Sort by blended score
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def map_obligations(self,
                       obligations: List[Any],
                       k: int = 5,
                       threshold_high: float = 0.75,
                       threshold_low: float = 0.60) -> Dict[str, List[ControlMapping]]:
        """
        Map obligations to controls
        
        Args:
            obligations: List of Obligation objects
            k: Top-k controls to return per obligation
            threshold_high: Auto-accept threshold
            threshold_low: Below this requires review
        
        Returns:
            Dictionary mapping obligation section_id to list of ControlMappings
        """
        mappings = {}
        
        for obligation in obligations:
            search_results = self.search_controls(obligation.text, k=k)
            
            obligation_mappings = []
            
            for control, blended_score, cosine_score, lexical_score in search_results:
                # Determine initial status based on threshold
                if blended_score >= threshold_high:
                    status = 'accepted'
                elif blended_score >= threshold_low:
                    status = 'review'
                else:
                    status = 'rejected'
                
                mapping = ControlMapping(
                    obligation_text=obligation.text,
                    control_id=control.control_id,
                    control_title=control.title,
                    score=blended_score,
                    cosine_score=cosine_score,
                    lexical_score=lexical_score,
                    status=status
                )
                
                obligation_mappings.append(mapping)
            
            mappings[obligation.section_id] = obligation_mappings
            
            logger.debug(
                f"Mapped {len(obligation_mappings)} controls to obligation "
                f"{obligation.section_id}"
            )
        
        logger.info(f"Completed mapping for {len(obligations)} obligations")
        return mappings
    
    def get_mapping_stats(self, mappings: Dict[str, List[ControlMapping]]) -> Dict[str, Any]:
        """Get statistics about mappings"""
        all_mappings = [m for maps in mappings.values() for m in maps]
        
        if not all_mappings:
            return {
                'total_mappings': 0,
                'by_status': {'accepted': 0, 'review': 0, 'rejected': 0},
                'avg_score': 0.0
            }
        
        stats = {
            'total_mappings': len(all_mappings),
            'by_status': {
                'accepted': sum(1 for m in all_mappings if m.status == 'accepted'),
                'review': sum(1 for m in all_mappings if m.status == 'review'),
                'rejected': sum(1 for m in all_mappings if m.status == 'rejected')
            },
            'avg_score': sum(m.score for m in all_mappings) / len(all_mappings),
            'top_score': max(m.score for m in all_mappings),
            'obligations_with_mappings': len(mappings)
        }
        
        return stats


def create_mapper(catalog_dir: Path,
                 catalog_files: List[str],
                 cosine_weight: float = 0.7,
                 lexical_weight: float = 0.3) -> MapperAgent:
    """Create mapper agent instance"""
    return MapperAgent(catalog_dir, catalog_files, cosine_weight, lexical_weight)
