import React from "react";
import { PageLayout } from "../../components/layout";
import { Topology } from "../Topology";

export function TopologyPage() {
  return (
    <PageLayout module="monitor" fullWidth>
      <Topology />
    </PageLayout>
  );
}

export default TopologyPage;
