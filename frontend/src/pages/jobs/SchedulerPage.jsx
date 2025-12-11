import React from "react";
import { PageLayout } from "../../components/layout";
import { Scheduler } from "../Scheduler";

export function SchedulerPage() {
  return (
    <PageLayout module="jobs">
      <Scheduler />
    </PageLayout>
  );
}

export default SchedulerPage;
