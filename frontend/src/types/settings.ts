export interface GeminiTestResponse {
  connection_status: string;
  model_name: string;
  response: string;
  response_time_ms: number;
}

export interface AiPreferences {
  explanationDetail: 'concise' | 'detailed';
  autoSuggestActions: boolean;
  includeEvidence: boolean;
}

export interface BusinessProfile {
  businessName: string;
  businessEmail: string;
  industry: string;
  timezone: string;
  currency: string;
  fiscalPeriod: string;
}

export interface UserProfile {
  name: string;
  role: string;
  department: string;
  email: string;
  capabilities: string[];
}

export interface NotificationChannelSetting {
  id: string;
  title: string;
  description: string;
  category: string;
  emailEnabled: boolean;
  inAppEnabled: boolean;
  status: 'planned' | 'active';
}
