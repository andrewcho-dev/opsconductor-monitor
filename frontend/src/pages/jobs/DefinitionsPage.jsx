import React from "react";
import { PageLayout } from "../../components/layout";
import JobDefinitions from "../JobDefinitions";

export function DefinitionsPage() {
  return (
    <PageLayout module="jobs">
      <JobDefinitions />
    </PageLayout>
  );
}

export default DefinitionsPage;
