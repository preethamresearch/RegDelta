"""
RegDelta Actions Agent
Generate action plans and evidence schedules from mappings
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from agents.mapper import ControlMapping
from agents.extractor import Obligation

logger = logging.getLogger(__name__)


@dataclass
class Action:
    """Represents an action item"""
    summary: str
    obligation_text: str
    control_id: str
    owner: str
    due_date: str
    priority: str  # 'high', 'medium', 'low'
    system: str
    status: str = 'planned'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'summary': self.summary,
            'obligation_text': self.obligation_text[:150] + '...',
            'control_id': self.control_id,
            'owner': self.owner,
            'due_date': self.due_date,
            'priority': self.priority,
            'system': self.system,
            'status': self.status
        }


@dataclass
class EvidenceRun:
    """Represents a recurring evidence collection schedule"""
    control_id: str
    artefact: str
    owner: str
    cadence_cron: str
    next_run_at: str
    status: str = 'scheduled'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'control_id': self.control_id,
            'artefact': self.artefact,
            'owner': self.owner,
            'cadence_cron': self.cadence_cron,
            'next_run_at': self.next_run_at,
            'status': self.status
        }


class ActionsAgent:
    """Generate actions and evidence schedules"""
    
    def __init__(self, default_due_days: int = 30):
        self.default_due_days = default_due_days
        logger.info(f"ActionsAgent initialized with {default_due_days} day default deadline")
    
    def generate_actions(self,
                        obligations: List[Obligation],
                        mappings: Dict[str, List[ControlMapping]],
                        controls_catalog: List[Any]) -> List[Action]:
        """
        Generate action items from obligations and mappings
        
        Args:
            obligations: List of extracted obligations
            mappings: Mapping results (section_id -> ControlMappings)
            controls_catalog: Full control catalog for owner lookup
        
        Returns:
            List of Action items
        """
        actions = []
        control_lookup = {ctrl.control_id: ctrl for ctrl in controls_catalog}
        
        for obligation in obligations:
            section_mappings = mappings.get(obligation.section_id, [])
            
            # Get accepted mappings
            accepted = [m for m in section_mappings if m.status == 'accepted']
            
            if not accepted:
                # Create action for unmapped obligation
                action = self._create_gap_action(obligation)
                actions.append(action)
            else:
                # Create actions for each accepted mapping
                for mapping in accepted:
                    control = control_lookup.get(mapping.control_id)
                    if control:
                        action = self._create_mapping_action(
                            obligation, mapping, control
                        )
                        actions.append(action)
        
        logger.info(f"Generated {len(actions)} actions")
        return actions
    
    def _create_mapping_action(self,
                               obligation: Obligation,
                               mapping: ControlMapping,
                               control: Any) -> Action:
        """Create action for a mapped obligation"""
        
        # Determine priority from obligation severity
        priority = obligation.severity
        
        # Calculate due date based on priority
        if priority == 'high':
            days = 14
        elif priority == 'medium':
            days = 30
        else:
            days = 60
        
        due_date = (datetime.utcnow() + timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Generate summary
        summary = f"Implement/verify {control.title} for new obligation"
        
        return Action(
            summary=summary,
            obligation_text=obligation.text,
            control_id=control.control_id,
            owner=control.owner,
            due_date=due_date,
            priority=priority,
            system=control.domain,
            status='planned'
        )
    
    def _create_gap_action(self, obligation: Obligation) -> Action:
        """Create action for unmapped (gap) obligation"""
        
        priority = obligation.severity
        
        # Gaps are urgent
        if priority == 'high':
            days = 7
        elif priority == 'medium':
            days = 14
        else:
            days = 30
        
        due_date = (datetime.utcnow() + timedelta(days=days)).strftime('%Y-%m-%d')
        
        summary = "REVIEW: New obligation without control mapping"
        
        return Action(
            summary=summary,
            obligation_text=obligation.text,
            control_id="GAP",
            owner="Compliance Team",
            due_date=due_date,
            priority='high',  # Always high priority for gaps
            system="Compliance",
            status='review_required'
        )
    
    def generate_evidence_schedules(self,
                                   controls_used: List[Any],
                                   cadence_preset: str = 'quarterly') -> List[EvidenceRun]:
        """
        Generate evidence collection schedules for controls
        
        Args:
            controls_used: List of Control objects that need evidence
            cadence_preset: Default cadence ('monthly', 'quarterly', 'annual')
        
        Returns:
            List of EvidenceRun schedules
        """
        evidence_runs = []
        
        # Map cadence presets to cron expressions
        cadence_map = {
            'monthly': '0 0 1 * *',      # 1st of each month
            'quarterly': '0 0 1 */3 *',  # 1st of every 3rd month
            'annual': '0 0 1 1 *'        # January 1st
        }
        
        cron_expr = cadence_map.get(cadence_preset, cadence_map['quarterly'])
        
        for control in controls_used:
            # Create schedule for each evidence example
            for artefact in control.evidence_examples[:2]:  # Limit to top 2
                next_run = self._calculate_next_run(cadence_preset)
                
                evidence_run = EvidenceRun(
                    control_id=control.control_id,
                    artefact=artefact,
                    owner=control.owner,
                    cadence_cron=cron_expr,
                    next_run_at=next_run,
                    status='scheduled'
                )
                
                evidence_runs.append(evidence_run)
        
        logger.info(f"Generated {len(evidence_runs)} evidence schedules")
        return evidence_runs
    
    def _calculate_next_run(self, cadence: str) -> str:
        """Calculate next run date based on cadence"""
        now = datetime.utcnow()
        
        if cadence == 'monthly':
            # Next month, 1st day
            if now.month == 12:
                next_date = datetime(now.year + 1, 1, 1)
            else:
                next_date = datetime(now.year, now.month + 1, 1)
        
        elif cadence == 'quarterly':
            # Next quarter
            current_quarter = (now.month - 1) // 3
            next_quarter = (current_quarter + 1) % 4
            if next_quarter == 0:
                next_date = datetime(now.year + 1, 1, 1)
            else:
                next_date = datetime(now.year, next_quarter * 3 + 1, 1)
        
        elif cadence == 'annual':
            # Next year
            next_date = datetime(now.year + 1, 1, 1)
        
        else:
            # Default: 30 days from now
            next_date = now + timedelta(days=30)
        
        return next_date.strftime('%Y-%m-%d')
    
    def get_action_summary(self, actions: List[Action]) -> Dict[str, Any]:
        """Get summary statistics for actions"""
        if not actions:
            return {
                'total': 0,
                'by_priority': {'high': 0, 'medium': 0, 'low': 0},
                'by_status': {},
                'gaps': 0
            }
        
        summary = {
            'total': len(actions),
            'by_priority': {
                'high': sum(1 for a in actions if a.priority == 'high'),
                'medium': sum(1 for a in actions if a.priority == 'medium'),
                'low': sum(1 for a in actions if a.priority == 'low')
            },
            'by_status': {
                'planned': sum(1 for a in actions if a.status == 'planned'),
                'review_required': sum(1 for a in actions if a.status == 'review_required')
            },
            'gaps': sum(1 for a in actions if a.control_id == 'GAP'),
            'unique_owners': len(set(a.owner for a in actions)),
            'unique_systems': len(set(a.system for a in actions))
        }
        
        return summary
    
    def get_evidence_summary(self, evidence_runs: List[EvidenceRun]) -> Dict[str, Any]:
        """Get summary statistics for evidence schedules"""
        if not evidence_runs:
            return {
                'total': 0,
                'unique_controls': 0,
                'unique_owners': 0
            }
        
        summary = {
            'total': len(evidence_runs),
            'unique_controls': len(set(e.control_id for e in evidence_runs)),
            'unique_owners': len(set(e.owner for e in evidence_runs)),
            'by_owner': {}
        }
        
        # Count by owner
        for run in evidence_runs:
            summary['by_owner'][run.owner] = summary['by_owner'].get(run.owner, 0) + 1
        
        return summary


def create_actions_agent(default_due_days: int = 30) -> ActionsAgent:
    """Create actions agent instance"""
    return ActionsAgent(default_due_days)
