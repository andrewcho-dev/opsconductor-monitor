import React from 'react';
import { PageLayout } from '../../components/layout';
import ActiveJobs from '../ActiveJobs';

export default function ActiveJobsPage() {
  return (
    <PageLayout module="monitor">
      <ActiveJobs />
    </PageLayout>
  );
}
