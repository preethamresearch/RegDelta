"""
RegDelta Planner Agent
Orchestrates the workflow: ingest → diff → extract → map → plan
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from utils.config import Config
from utils.audit import AuditLogger
from utils.pdf_extractor import extract_text, paragraphize
from utils.diff import diff
from agents.extractor import ExtractorAgent, Obligation
from agents.mapper import MapperAgent, ControlMapping

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


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle numpy types"""
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
        except ImportError:
            pass
        return super().default(obj)


class PlannerAgent:
    """Orchestrates the RegDelta workflow"""
    
    def __init__(self, config: Config, audit_logger: AuditLogger):
        self.config = config
        self.audit = audit_logger
        
        # Initialize agents
        self.extractor: Optional[ExtractorAgent] = None
        self.mapper: Optional[MapperAgent] = None
        
        # State
        self.current_scenario: Optional[str] = None
        self.baseline_doc: Optional[Dict[str, Any]] = None
        self.new_doc: Optional[Dict[str, Any]] = None
        self.diff_result: Optional[Any] = None
        self.obligations: List[Obligation] = []
        self.mappings: Dict[str, List[ControlMapping]] = {}
        
        logger.info("PlannerAgent initialized")
    
    def initialize_agents(self):
        """Initialize extractor and mapper agents"""
        # Initialize extractor
        lexicon_file = self.config.lexicon_file
        self.extractor = ExtractorAgent(lexicon_file)
        
        self.audit.log(
            actor="system",
            action="agent_init",
            payload={"agent": "extractor", "lexicon": str(lexicon_file)}
        )
        
        # Initialize mapper
        self.mapper = MapperAgent(
            catalog_dir=self.config.catalog_dir,
            catalog_files=self.config.catalogs,
            cosine_weight=self.config.blend_weights['cosine'],
            lexical_weight=self.config.blend_weights['lexical']
        )
        
        self.audit.log(
            actor="system",
            action="agent_init",
            payload={
                "agent": "mapper",
                "catalogs": self.config.catalogs,
                "controls_loaded": len(self.mapper.controls)
            }
        )
        
        # Build mapper index
        logger.info("Building mapper index (this may take a moment)...")
        self.mapper.build_index()
        
        self.audit.log(
            actor="system",
            action="index_built",
            payload={"vectors": len(self.mapper.controls)}
        )
        
        logger.info("All agents initialized successfully")
    
    def stage_ingest(self, 
                    baseline_pdf: Optional[Path] = None,
                    new_pdf: Optional[Path] = None,
                    scenario_name: str = "default") -> Dict[str, Any]:
        """
        Stage 1: Ingest PDFs and extract text
        
        Args:
            baseline_pdf: Path to baseline PDF (optional for first scenario)
            new_pdf: Path to new PDF
            scenario_name: Scenario identifier
        
        Returns:
            Ingestion summary
        """
        self.current_scenario = scenario_name
        
        logger.info(f"Stage 1: Ingesting documents for scenario '{scenario_name}'")
        
        summary = {
            'scenario': scenario_name,
            'baseline': None,
            'new': None,
            'errors': []
        }
        
        # Ingest baseline
        if baseline_pdf:
            try:
                text, extractor = extract_text(baseline_pdf, self.config.skip_on_error)
                paragraphs = paragraphize(text)
                
                self.baseline_doc = {
                    'path': str(baseline_pdf),
                    'text': text,
                    'paragraphs': paragraphs,
                    'extractor': extractor,
                    'ingested_at': datetime.utcnow().isoformat()
                }
                
                summary['baseline'] = {
                    'file': baseline_pdf.name,
                    'paragraphs': len(paragraphs),
                    'chars': len(text),
                    'extractor': extractor
                }
                
                self.audit.log(
                    actor="planner",
                    action="ingest_baseline",
                    payload=summary['baseline']
                )
                
            except Exception as e:
                logger.error(f"Failed to ingest baseline: {e}")
                summary['errors'].append(f"Baseline: {str(e)}")
        
        # Ingest new document
        if new_pdf:
            try:
                text, extractor = extract_text(new_pdf, self.config.skip_on_error)
                paragraphs = paragraphize(text)
                
                self.new_doc = {
                    'path': str(new_pdf),
                    'text': text,
                    'paragraphs': paragraphs,
                    'extractor': extractor,
                    'ingested_at': datetime.utcnow().isoformat()
                }
                
                summary['new'] = {
                    'file': new_pdf.name,
                    'paragraphs': len(paragraphs),
                    'chars': len(text),
                    'extractor': extractor
                }
                
                self.audit.log(
                    actor="planner",
                    action="ingest_new",
                    payload=summary['new']
                )
                
            except Exception as e:
                logger.error(f"Failed to ingest new document: {e}")
                summary['errors'].append(f"New document: {str(e)}")
        
        logger.info(f"Ingestion complete: {len(summary['errors'])} errors")
        return summary
    
    def stage_diff(self) -> Dict[str, Any]:
        """
        Stage 2: Compute diff between baseline and new
        
        Returns:
            Diff summary
        """
        logger.info("Stage 2: Computing diff")
        
        if not self.baseline_doc or not self.new_doc:
            logger.warning("Cannot diff: missing baseline or new document")
            return {'error': 'Missing documents'}
        
        baseline_paras = self.baseline_doc['paragraphs']
        new_paras = self.new_doc['paragraphs']
        
        self.diff_result = diff(baseline_paras, new_paras)
        summary = self.diff_result.get_summary()
        
        self.audit.log(
            actor="planner",
            action="compute_diff",
            payload=summary
        )
        
        logger.info(f"Diff complete: {summary['total_ops']} operations")
        return summary
    
    def stage_extract(self) -> Dict[str, Any]:
        """
        Stage 3: Extract obligations from new document
        
        Returns:
            Extraction summary
        """
        logger.info("Stage 3: Extracting obligations")
        
        if not self.extractor:
            raise RuntimeError("Extractor not initialized. Call initialize_agents() first.")
        
        if not self.new_doc:
            logger.warning("Cannot extract: missing new document")
            return {'error': 'Missing new document'}
        
        # Extract from new document paragraphs
        self.obligations = self.extractor.extract_from_paragraphs(
            self.new_doc['paragraphs']
        )
        
        stats = self.extractor.get_extraction_stats(self.obligations)
        
        self.audit.log(
            actor="extractor",
            action="extract_obligations",
            payload=stats
        )
        
        logger.info(f"Extraction complete: {stats['total']} obligations found")
        return stats
    
    def stage_map(self) -> Dict[str, Any]:
        """
        Stage 4: Map obligations to controls
        
        Returns:
            Mapping summary
        """
        logger.info("Stage 4: Mapping obligations to controls")
        
        if not self.mapper:
            raise RuntimeError("Mapper not initialized. Call initialize_agents() first.")
        
        if not self.obligations:
            logger.warning("No obligations to map")
            return {'error': 'No obligations'}
        
        # Map obligations
        self.mappings = self.mapper.map_obligations(
            obligations=self.obligations,
            k=self.config.top_k,
            threshold_high=self.config.mapping_thresholds['high'],
            threshold_low=self.config.mapping_thresholds['low']
        )
        
        stats = self.mapper.get_mapping_stats(self.mappings)
        
        self.audit.log(
            actor="mapper",
            action="map_obligations",
            payload=stats
        )
        
        logger.info(f"Mapping complete: {stats['total_mappings']} mappings created")
        return stats
    
    def run_full_pipeline(self,
                         baseline_pdf: Optional[Path],
                         new_pdf: Path,
                         scenario_name: str = "default") -> Dict[str, Any]:
        """
        Run the full pipeline: ingest → diff → extract → map
        
        Returns:
            Complete pipeline summary
        """
        logger.info("=" * 60)
        logger.info(f"Running full pipeline for scenario: {scenario_name}")
        logger.info("=" * 60)
        
        pipeline_start = datetime.utcnow()
        
        results = {
            'scenario': scenario_name,
            'started_at': pipeline_start.isoformat(),
            'stages': {}
        }
        
        try:
            # Initialize agents if not already done
            if not self.extractor or not self.mapper:
                self.initialize_agents()
            
            # Stage 1: Ingest
            results['stages']['ingest'] = self.stage_ingest(
                baseline_pdf, new_pdf, scenario_name
            )
            
            # Stage 2: Diff (skip if no baseline)
            if baseline_pdf:
                results['stages']['diff'] = self.stage_diff()
            else:
                logger.info("Skipping diff (no baseline)")
                results['stages']['diff'] = {'skipped': True}
            
            # Stage 3: Extract
            results['stages']['extract'] = self.stage_extract()
            
            # Stage 4: Map
            results['stages']['map'] = self.stage_map()
            
            # Calculate duration
            pipeline_end = datetime.utcnow()
            duration = (pipeline_end - pipeline_start).total_seconds()
            
            results['completed_at'] = pipeline_end.isoformat()
            results['duration_seconds'] = duration
            results['status'] = 'success'
            
            logger.info("=" * 60)
            logger.info(f"Pipeline completed in {duration:.2f} seconds")
            logger.info("=" * 60)
            
            self.audit.log(
                actor="planner",
                action="pipeline_complete",
                payload={'duration': duration, 'scenario': scenario_name}
            )
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            results['status'] = 'failed'
            results['error'] = str(e)
            
            self.audit.log(
                actor="planner",
                action="pipeline_failed",
                payload={'error': str(e), 'scenario': scenario_name}
            )
        
        return results
    
    def save_state(self, output_dir: Path):
        """Save current state to JSON files"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save obligations
        if self.obligations:
            try:
                obligations_file = output_dir / f"{self.current_scenario}_obligations.json"
                with open(obligations_file, 'w', encoding='utf-8') as f:
                    obligations_data = [ob.to_dict() for ob in self.obligations]
                    obligations_data = convert_to_serializable(obligations_data)
                    json.dump(obligations_data, f, indent=2)
                logger.info(f"Saved obligations to {obligations_file}")
            except Exception as e:
                logger.error(f"Failed to save obligations: {e}")
                raise
        
        # Save mappings
        if self.mappings:
            try:
                mappings_file = output_dir / f"{self.current_scenario}_mappings.json"
                mappings_data = {
                    section_id: [m.to_dict() for m in maps]
                    for section_id, maps in self.mappings.items()
                }
                mappings_data = convert_to_serializable(mappings_data)
                with open(mappings_file, 'w', encoding='utf-8') as f:
                    json.dump(mappings_data, f, indent=2)
                logger.info(f"Saved mappings to {mappings_file}")
            except Exception as e:
                logger.error(f"Failed to save mappings: {e}")
                raise
        
        # Save diff
        if self.diff_result:
            try:
                diff_file = output_dir / f"{self.current_scenario}_diff.json"
                diff_data = convert_to_serializable(self.diff_result.to_dict())
                with open(diff_file, 'w', encoding='utf-8') as f:
                    json.dump(diff_data, f, indent=2)
                logger.info(f"Saved diff to {diff_file}")
            except Exception as e:
                logger.error(f"Failed to save diff: {e}")
                raise

