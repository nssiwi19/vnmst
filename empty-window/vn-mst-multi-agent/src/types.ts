export type VietQrBusiness = {
  id: string;
  name: string;
  internationalName: string;
  shortName: string;
  address: string;
};

export type VietQrResponse = {
  code: string;
  desc: string;
  data: VietQrBusiness | null;
};

export type ResearchOutput = {
  legalForm: string;
  inferredSector: string;
  region: string;
  profileBullets: string[];
  dataSources: string[];
};

export type ReportOutput = {
  executiveSummary: string;
  recommendations: string[];
  keyEntities: { label: string; value: string }[];
};

export type VerificationOutput = {
  trustScore: number;
  riskFlags: { level: "low" | "medium" | "high"; message: string }[];
  complianceNotes: string[];
};

export type PipelineState = {
  mst: string;
  raw: VietQrResponse | null;
  research: ResearchOutput | null;
  report: ReportOutput | null;
  verification: VerificationOutput | null;
  step:
    | "idle"
    | "fetching"
    | "research"
    | "report"
    | "verification"
    | "done"
    | "error";
  error: string | null;
};

export type CrmPurpose = "kyc" | "credit" | "audit" | "partnership";

export type CrmSegment = "Enterprise" | "SME" | "Startup" | "Risky" | "Inactive";

export type CrmInsight = {
  segment: CrmSegment;
  rationale: string[];
  purposeAdjustments: string[];
  suggestedNextSteps: string[];
};

export type SampleCompany = {
  id: string;
  label: string;
  mst: string;
  note: string;
};
