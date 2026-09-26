import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000";

export interface AnalyzeRequest {
  repo_path: string;
  changed_files: string[];
}

export interface Recommendation {
  category: "TEST" | "REVIEW";
  module: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  action: string;
  reason: string;
}

export interface AnalyzeData {
  changed_files: string[];
  changed_modules: string[];
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  impact_score: number;
  affected_count: number;
  direct_count: number;
  indirect_count: number;
  max_depth: number;
  direct_affected: string[];
  indirect_affected: string[];
  all_affected: string[];
  evidence: string[];
  recommendations: Recommendation[];
  unknown_files: string[];
}

export interface AnalyzeResponse {
  success: boolean;
  data: AnalyzeData;
}

export async function analyzeRepository(
  request: AnalyzeRequest
): Promise<AnalyzeData> {
  const response = await axios.post<AnalyzeResponse>(
    `${API_BASE_URL}/analyze`,
    request
  );

  if (!response.data.success) {
    throw new Error("ImpactOS analysis failed");
  }

  return response.data.data;
}