import React from "react";
import { PageLayout } from "../../components/layout";
import WorkflowsList from "./WorkflowsList";

export function WorkflowsListPage() {
  return (
    <PageLayout module="workflows" fullWidth>
      <WorkflowsList />
    </PageLayout>
  );
}

export default WorkflowsListPage;
