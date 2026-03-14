"""
Template Generator Service
Generates document templates relevant to legal issues
"""

import json
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DocumentTemplate:
    """Represents a document template."""
    
    def __init__(
        self,
        template_id: str,
        name: str,
        description: str,
        file_format: str = "docx",
        jurisdiction: str = "India",
        applicable_issues: List[str] = None,
        category: str = ""
    ):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.file_format = file_format
        self.jurisdiction = jurisdiction
        self.applicable_issues = applicable_issues or []
        self.category = category
    
    def to_dict(self):
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "file_format": self.file_format,
            "jurisdiction": self.jurisdiction,
            "applicable_issues": self.applicable_issues,
            "category": self.category,
            "download_url": f"/api/templates/{self.template_id}"
        }


class TemplateGenerator:
    """
    Generates list of relevant document templates for legal issues
    """
    
    # Define all available templates
    TEMPLATES = {
        "complaint_letter": DocumentTemplate(
            template_id="complaint_letter",
            name="Formal Complaint Letter",
            description="Template for writing formal complaint to other party",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["dowry_harassment", "harassment_civil", "property_dispute"],
            category="correspondence"
        ),
        "demand_letter": DocumentTemplate(
            template_id="demand_letter",
            name="Legal Demand Letter",
            description="Professional demand letter for financial claims or dispute resolution",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["property_dispute", "financial_dispute", "harassment_civil"],
            category="correspondence"
        ),
        "notice_to_party": DocumentTemplate(
            template_id="notice_to_party",
            name="Notice to Other Party",
            description="Formal legal notice to other party regarding dispute",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["all"],
            category="correspondence"
        ),
        "evidence_collection_sheet": DocumentTemplate(
            template_id="evidence_collection_sheet",
            name="Evidence Collection & Organization Sheet",
            description="Worksheet to collect, organize, and document all evidence",
            file_format="xlsx",
            jurisdiction="India",
            applicable_issues=["all"],
            category="documentation"
        ),
        "timeline_document": DocumentTemplate(
            template_id="timeline_document",
            name="Incident Timeline Document",
            description="Template to record all incidents chronologically with dates and details",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["all"],
            category="documentation"
        ),
        "witness_statement": DocumentTemplate(
            template_id="witness_statement",
            name="Witness Statement Template",
            description="Template for witnesses to provide written statements about incidents",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["all"],
            category="documentation"
        ),
        "agreement_settlement": DocumentTemplate(
            template_id="agreement_settlement",
            name="Settlement Agreement Template",
            description="Template for settlement/compromise agreement between parties",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["harassment_civil", "property_dispute", "financial_dispute"],
            category="agreement"
        ),
        "fir_preparation": DocumentTemplate(
            template_id="fir_preparation",
            name="FIR Preparation Worksheet",
            description="Worksheet to prepare detailed information for FIR filing",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["criminal_complaint", "harassment_criminal", "dowry_harassment"],
            category="legal_process"
        ),
        "petition_divorce": DocumentTemplate(
            template_id="petition_divorce",
            name="Divorce Petition Template",
            description="Template for divorce petition (requires lawyer finalization)",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["divorce_contested", "divorce_amicable"],
            category="legal_petition"
        ),
        "maintenance_claim": DocumentTemplate(
            template_id="maintenance_claim",
            name="Maintenance (Alimony) Claim Form",
            description="Template for claiming maintenance/alimony during/after divorce",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["divorce_contested", "divorce_amicable"],
            category="legal_petition"
        ),
        "police_complaint_prepare": DocumentTemplate(
            template_id="police_complaint_prepare",
            name="Police Complaint Preparation Guide",
            description="Guide and template for preparing complaint before visiting police station",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["criminal_complaint", "harassment_criminal"],
            category="legal_process"
        ),
        "property_evidence_list": DocumentTemplate(
            template_id="property_evidence_list",
            name="Property Evidence Documentation Template",
            description="Specialized template for documenting property-related evidence",
            file_format="xlsx",
            jurisdiction="India",
            applicable_issues=["property_dispute"],
            category="documentation"
        ),
        "communication_log": DocumentTemplate(
            template_id="communication_log",
            name="Communication Log Template",
            description="Template to log all communications (calls, messages, meetings)",
            file_format="xlsx",
            jurisdiction="India",
            applicable_issues=["all"],
            category="documentation"
        ),
        "medical_report_guide": DocumentTemplate(
            template_id="medical_report_guide",
            name="Medical Evidence Documentation Guide",
            description="Guide for collecting and documenting medical evidence of harassment/injury",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["harassment_criminal", "dowry_harassment", "domestic_violence"],
            category="documentation"
        ),
        "financial_documentation": DocumentTemplate(
            template_id="financial_documentation",
            name="Financial Documentation Checklist",
            description="Checklist for gathering and organizing financial documents",
            file_format="xlsx",
            jurisdiction="India",
            applicable_issues=["property_dispute", "financial_dispute", "dowry_harassment"],
            category="documentation"
        ),
        "lawyer_consultation_guide": DocumentTemplate(
            template_id="lawyer_consultation_guide",
            name="Lawyer Consultation Preparation Guide",
            description="Guide to prepare questions and information for lawyer consultation",
            file_format="docx",
            jurisdiction="India",
            applicable_issues=["all"],
            category="guidance"
        ),
    }
    
    def __init__(self):
        logger.info(f"TemplateGenerator initialized with {len(self.TEMPLATES)} templates")
    
    def generate_templates(
        self,
        extracted_features: Dict,
        country: str = "India"
    ) -> List[DocumentTemplate]:
        """
        Generate list of relevant templates based on issue type and features
        
        Args:
            extracted_features: Dict with legal features
            country: Jurisdiction country
            
        Returns:
            List of relevant DocumentTemplate objects
        """
        
        # Determine issue type from features
        issue_type = self._determine_issue_type(extracted_features)
        logger.debug(f"Determined issue type for templates: {issue_type}")
        
        # Find all templates applicable to this issue
        relevant_templates = []
        
        for template in self.TEMPLATES.values():
            # Check country match
            if template.jurisdiction != country and country != "India":
                continue
            
            # Check if issue applicability matches
            if "all" in template.applicable_issues or issue_type in template.applicable_issues:
                relevant_templates.append(template)
        
        # Prioritize templates based on severity and features
        relevant_templates = self._prioritize_templates(
            relevant_templates, extracted_features
        )
        
        logger.info(f"Generated {len(relevant_templates)} relevant templates for {issue_type}")
        return relevant_templates
    
    def _determine_issue_type(self, features: Dict) -> str:
        """Determine issue type from features (same as checklist generator)"""
        
        if features.get("has_dowry"):
            return "dowry_harassment"
        if features.get("has_custody"):
            return "child_custody"
        if features.get("has_marriage_issue") or features.get("is_family_matter"):
            return "divorce_contested" if features.get("severity_level") == "high" else "divorce_amicable"
        if features.get("has_harassment"):
            return "harassment_criminal" if features.get("has_criminal_aspect") else "harassment_civil"
        if features.get("has_property_damage"):
            return "property_dispute"
        if features.get("has_threat") or (features.get("severity_level") == "high" and features.get("has_criminal_aspect")):
            return "criminal_complaint"
        if features.get("is_employment_matter"):
            return "employment_dispute"
        
        return "general_legal_matter"
    
    def _prioritize_templates(
        self,
        templates: List[DocumentTemplate],
        features: Dict
    ) -> List[DocumentTemplate]:
        """
        Prioritize templates based on severity and features
        
        Order templates by importance:
        1. Critical/immediate templates (based on severity)
        2. Documentation templates (always useful)
        3. Guidance/preparation templates
        """
        
        critical_priority = []
        documentation_priority = []
        guidance_priority = []
        
        for template in templates:
            if template.category == "legal_process":
                # Criminal processes are critical
                if features.get("has_criminal_aspect") or features.get("severity_level") in ["high", "critical"]:
                    critical_priority.append(template)
                else:
                    documentation_priority.append(template)
            elif template.category == "documentation":
                documentation_priority.append(template)
            else:
                guidance_priority.append(template)
        
        # Combine in priority order
        prioritized = critical_priority + documentation_priority + guidance_priority
        
        # Return top 6-8 templates (most relevant)
        return prioritized[:8]
    
    def get_template(self, template_id: str) -> Optional[DocumentTemplate]:
        """Get a specific template by ID"""
        return self.TEMPLATES.get(template_id)
    
    def get_all_templates(self) -> List[DocumentTemplate]:
        """Get all available templates"""
        return list(self.TEMPLATES.values())
    
    def get_templates_by_category(self, category: str) -> List[DocumentTemplate]:
        """Get templates by category"""
        return [t for t in self.TEMPLATES.values() if t.category == category]


# Singleton instance
_generator = None


def get_template_generator() -> TemplateGenerator:
    """Get or create singleton generator instance"""
    global _generator
    if _generator is None:
        _generator = TemplateGenerator()
    return _generator
