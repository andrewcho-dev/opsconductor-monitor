import React from "react";
import { PageLayout } from "../../components/layout";
import { PowerTrends } from "../PowerTrends";

export function PowerTrendsPage() {
  return (
    <PageLayout module="monitor" fullWidth>
      <PowerTrends />
    </PageLayout>
  );
}

export default PowerTrendsPage;
