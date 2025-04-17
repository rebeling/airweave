export interface Connection {
  id: string;
  name: string;
  organization_id: string;
  created_by_email: string;
  modified_by_email: string;
  status: "active" | "inactive" | "error";
  integration_type: string;
  integration_credential_id: string;
  source_id: string;
  short_name: string;
  modified_at: string;
  lastSync?: string;
  syncCount?: number;
  documentsCount?: number;
  healthScore?: number;
  createdAt: string;
}

interface DataSourceCardProps {
  shortName: string;
  name: string;
  description: string;
  status: "connected" | "disconnected";
  onConnect?: () => void;
  onSelect?: () => void;
  existingConnections?: Connection[];
}
