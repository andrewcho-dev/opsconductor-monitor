import React from 'react';
import { PageLayout } from '../../components/layout';
import JobHistory from '../JobHistory';

export default function JobHistoryPage() {
  return (
    <PageLayout module="monitor">
      <JobHistory />
    </PageLayout>
  );
}
