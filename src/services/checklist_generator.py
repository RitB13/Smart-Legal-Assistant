"""
Checklist Generator Service
Generates actionable checklists based on legal issue type and jurisdiction
"""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ChecklistItem:
    """Represents a single checklist item."""
    
    def __init__(
        self,
        step_number: int,
        action: str,
        details: List[str],
        priority: str = "medium",
        timeline: str = "within 1 week",
        reference_law: Optional[str] = None
    ):
        self.step_number = step_number
        self.action = action
        self.details = details
        self.priority = priority  # critical, high, medium, low
        self.timeline = timeline
        self.reference_law = reference_law
    
    def to_dict(self):
        return {
            "step_number": self.step_number,
            "action": self.action,
            "details": self.details,
            "priority": self.priority,
            "timeline": self.timeline,
            "reference_law": self.reference_law
        }


class ChecklistGenerator:
    """
    Generates jurisdiction-specific legal action checklists
    """
    
    def __init__(self):
        self.checklists = {}
        self._load_checklists()
    
    def _load_checklists(self):
        """Load all checklist templates"""
        base_path = Path(__file__).parent.parent / "data" / "checklists"
        
        if not base_path.exists():
            logger.warning(f"Checklists directory not found: {base_path}")
            return
        
        # Load JSON files
        for file_path in base_path.glob("**/*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    checklist_data = json.load(f)
                    key = file_path.stem
                    self.checklists[key] = checklist_data
                    logger.debug(f"Loaded checklist: {key}")
            except Exception as e:
                logger.error(f"Failed to load checklist from {file_path}: {e}")
        
        logger.info(f"Loaded {len(self.checklists)} checklists")
    
    def generate_checklist(
        self,
        extracted_features: Dict,
        country: str = "India",
        state: str = "National"
    ) -> List[ChecklistItem]:
        """
        Generate checklist based on legal issue type and features
        
        Args:
            extracted_features: Dict with legal features (severity, type, etc.)
            country: Jurisdiction country
            state: Jurisdiction state
            
        Returns:
            List of ChecklistItem objects
        """
        checklist = []
        
        # Determine issue type from features
        issue_type = self._determine_issue_type(extracted_features)
        logger.debug(f"Determined issue type: {issue_type}")
        
        # Get base checklist for issue type
        base_checklist = self._get_base_checklist(issue_type)
        
        if not base_checklist:
            # Generate default checklist if no template
            return self._generate_default_checklist(extracted_features, country)
        
        # Build checklist from template
        checklist = self._build_checklist_from_template(
            base_checklist, extracted_features, country, state
        )
        
        return checklist
    
    def _determine_issue_type(self, features: Dict) -> str:
        """Determine issue type from features"""
        
        # Check for specific issue types
        if features.get("has_dowry"):
            return "dowry_harassment"
        
        if features.get("has_custody"):
            return "child_custody"
        
        if features.get("has_marriage_issue") or features.get("is_family_matter"):
            if features.get("severity_level") == "high":
                return "divorce_contested"
            return "divorce_amicable"
        
        if features.get("has_harassment"):
            if features.get("has_criminal_aspect"):
                return "harassment_criminal"
            return "harassment_civil"
        
        if features.get("has_property_damage"):
            return "property_dispute"
        
        if features.get("has_threat") or (features.get("severity_level") == "high" and features.get("has_criminal_aspect")):
            return "criminal_complaint"
        
        if features.get("is_employment_matter"):
            return "employment_dispute"
        
        return "general_legal_matter"
    
    def _get_base_checklist(self, issue_type: str) -> Optional[Dict]:
        """Get base checklist template for issue type"""
        # Try to find matching checklist
        for key, checklist in self.checklists.items():
            if issue_type in key or key in issue_type:
                return checklist
        
        return None
    
    def _build_checklist_from_template(
        self,
        template: Dict,
        features: Dict,
        country: str,
        state: str
    ) -> List[ChecklistItem]:
        """Build checklist from template with customization"""
        
        checklist = []
        step_num = 1
        
        # Add base steps
        for step in template.get("base_steps", []):
            checklist.append(
                ChecklistItem(
                    step_number=step_num,
                    action=step.get("action", ""),
                    details=step.get("details", []),
                    priority=step.get("priority", "medium"),
                    timeline=step.get("timeline", "within 1 week"),
                    reference_law=step.get("reference_law")
                )
            )
            step_num += 1
        
        # Add jurisdiction-specific steps
        jurisdiction_key = f"{country.lower()}_{state.lower()}" if state != "National" else country.lower()
        jurisdiction_steps = template.get("jurisdiction_additions", {}).get(country, [])
        
        for step in jurisdiction_steps:
            if isinstance(step, str):
                checklist.append(
                    ChecklistItem(
                        step_number=step_num,
                        action=step,
                        details=[],
                        priority="high",
                        timeline="within 2 weeks"
                    )
                )
            else:
                checklist.append(
                    ChecklistItem(
                        step_number=step_num,
                        action=step.get("action", ""),
                        details=step.get("details", []),
                        priority=step.get("priority", "high"),
                        timeline=step.get("timeline", "within 2 weeks")
                    )
                )
            step_num += 1
        
        # Add conditional steps based on severity/features
        if features.get("severity_level") == "high" and not any(
            "lawyer" in item.action.lower() for item in checklist
        ):
            checklist.insert(
                1,
                ChecklistItem(
                    step_number=1,
                    action="Consult with qualified lawyer urgently",
                    details=[
                        "Book consultation within 24-48 hours",
                        "Prepare all relevant documents",
                        "List all evidence/witnesses"
                    ],
                    priority="critical",
                    timeline="within 24-48 hours"
                )
            )
            # Renumber subsequent items
            for i, item in enumerate(checklist[1:], 2):
                item.step_number = i
        
        return checklist
    
    def _generate_default_checklist(
        self,
        features: Dict,
        country: str
    ) -> List[ChecklistItem]:
        """Generate default checklist for unknown issue types"""
        
        checklist = []
        step = 1
        
        # Step 1: Document everything
        checklist.append(
            ChecklistItem(
                step_number=step,
                action="Document all evidence and timeline",
                details=[
                    "Write down all events chronologically with dates",
                    "Keep copies of all communications (emails, msgs, etc.)",
                    "Take photos/videos of any damage or evidence",
                    "Save all documents in safe location"
                ],
                priority="critical",
                timeline="immediately"
            )
        )
        step += 1
        
        # Step 2: Consult lawyer if high severity
        if features.get("severity_level") in ["high", "critical"]:
            checklist.append(
                ChecklistItem(
                    step_number=step,
                    action="Schedule urgent consultation with lawyer",
                    details=[
                        "Contact 3-5 qualified lawyers",
                        "Prepare summary of issue",
                        "Ask about fees and timeline",
                        "Bring all relevant documents"
                    ],
                    priority="critical",
                    timeline="within 24-48 hours"
                )
            )
            step += 1
        else:
            checklist.append(
                ChecklistItem(
                    step_number=step,
                    action="Schedule consultation with lawyer",
                    details=[
                        "Research and contact local lawyers",
                        "Request initial consultation",
                        "Prepare case summary",
                        "Gather all documents"
                    ],
                    priority="high",
                    timeline="within 1 week"
                )
            )
            step += 1
        
        # Step 3: Send formal notice if applicable
        if features.get("has_financial_impact") or features.get("has_harassment"):
            checklist.append(
                ChecklistItem(
                    step_number=step,
                    action="Send formal notice to other party",
                    details=[
                        "Draft notice with lawyer's help",
                        "Send via registered mail/email with proof",
                        "Keep copy for records",
                        "Set deadline for response"
                    ],
                    priority="high",
                    timeline="within 2-3 weeks"
                )
            )
            step += 1
        
        # Step 4: File legal case if needed
        if features.get("has_criminal_aspect"):
            checklist.append(
                ChecklistItem(
                    step_number=step,
                    action=f"File complaint with police (First Information Report)",
                    details=[
                        "Visit local police station",
                        "File FIR with all details",
                        "Get copy of FIR for records",
                        "Follow up on investigation"
                    ],
                    priority="critical",
                    timeline=f"within 2 years (statute of limitations varies by {country} law)"
                )
            )
            step += 1
        else:
            checklist.append(
                ChecklistItem(
                    step_number=step,
                    action="File civil case if settlement fails",
                    details=[
                        "Work with lawyer to draft petition",
                        "File in appropriate court",
                        "Pay applicable court fees",
                        "Attend hearings regularly"
                    ],
                    priority="medium",
                    timeline="within 3-6 months"
                )
            )
            step += 1
        
        # Step 5: Gather evidence and witnesses
        checklist.append(
            ChecklistItem(
                step_number=step,
                action="Prepare evidence and witness list",
                details=[
                    "List all witnesses with contact info",
                    "Organize all documents chronologically",
                    "Get certificates/documents from authorities",
                    "Prepare affidavits from witnesses if needed"
                ],
                priority="high",
                timeline="before first hearing"
            )
        )
        step += 1
        
        return checklist
    
    def get_checklist_by_type(self, issue_type: str) -> Optional[Dict]:
        """Get a checklist template by issue type"""
        return next(
            (checklist for key, checklist in self.checklists.items() 
             if issue_type in key or key in issue_type),
            None
        )


# Singleton instance
_generator = None


def get_checklist_generator() -> ChecklistGenerator:
    """Get or create singleton generator instance"""
    global _generator
    if _generator is None:
        _generator = ChecklistGenerator()
    return _generator
