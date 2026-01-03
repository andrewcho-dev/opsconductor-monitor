import React from "react";
import { useParams } from "react-router-dom";
import { PageLayout, PageHeader } from "../../components/layout";
import { DeviceDetail } from "../DeviceDetail";
import { Server } from "lucide-react";

export function DeviceDetailPage() {
  const { ip } = useParams();

  return (
    <PageLayout module="inventory">
      <DeviceDetail />
    </PageLayout>
  );
}

export default DeviceDetailPage;
