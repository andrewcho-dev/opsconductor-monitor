import React from "react";
import { PageLayout } from "../../components/layout";
import WorkflowsList from "./WorkflowsList";

export function WorkflowsListPage() {
  return (
    <PageLayout module="workflows">
      <WorkflowsList />
    </PageLayout>
  );
}

export default WorkflowsListPage;
