export type DisputeStatus =
  | 'pending_party_b'
  | 'pending_statements'
  | 'pending_party_b_statement'
  | 'pending_party_a_statement'
  | 'analysis_running'
  | 'completed'
  | 'failed';

export interface CreateDisputeResponse {
  dispute_id: string;
  status: DisputeStatus;
  invite_code: string;
  message: string;
  created_at: string;
}

export interface DisputeStatusResponse {
  dispute_id: string;
  status: DisputeStatus;
  case_type: string;
  jurisdiction: string;
  party_a_submitted: boolean;
  party_b_submitted: boolean;
  party_b_joined: boolean;
  is_party_a: boolean;
  created_at: string;
  completed_at?: string;
}

export interface SettlementRange {
  low?: number;
  median?: number;
  high?: number;
  currency: string;
  confidence: number;
  basis: string;
}

export interface FairnessAudit {
  party_a_privilege_score: number;
  party_b_privilege_score: number;
  bias_detected: boolean;
  bias_direction: 'party_a' | 'party_b' | 'neutral';
  normalization_applied: boolean;
  note: string;
}

export interface AgreementPoint {
  point: string;
  confidence: number;
}

export interface ConflictPoint {
  point: string;
  party_a_position: string;
  party_b_position: string;
  severity: 'critical' | 'major' | 'minor';
}

export interface MediationReport {
  dispute_id: string;
  points_of_agreement: AgreementPoint[];
  points_of_conflict: ConflictPoint[];
  settlement_range: SettlementRange;
  proposed_settlement: string;
  proposed_settlement_rationale: string;
  applicable_laws: string[];
  fairness_audit: FairnessAudit;
  similar_precedents: string[];
  next_steps: string[];
  generated_at: string;
  model_version: string;
}

export interface DisputeResultResponse {
  dispute_id: string;
  status: DisputeStatus;
  report?: MediationReport;
  message: string;
}

export interface UserDisputeListItem {
  dispute_id: string;
  invite_code: string;
  status: DisputeStatus;
  case_type: string;
  role: 'party_a' | 'party_b';
  created_at: string;
  completed_at?: string;
}

export const CASE_TYPE_LABELS: Record<string, string> = {
  property: 'Property Dispute',
  money: 'Money / Loan',
  family: 'Family Matter',
  employment: 'Employment',
  consumer: 'Consumer Complaint',
  contract: 'Contract Breach',
  other: 'Other',
};

export const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
  'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
  'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
  'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Delhi', 'Jammu & Kashmir', 'Ladakh', 'Puducherry', 'Chandigarh',
];
