import React, { useState } from "react";
import { PageLayout, PageHeader } from "../../components/layout";
import { Bell, Filter, CheckCircle, AlertTriangle, XCircle, Clock } from "lucide-react";

export function AlertsPage() {
  const [alerts] = useState([
    // Sample alerts - would come from API
  ]);

  return (
    <PageLayout module="monitor">
      <PageHeader
        title="Alert History"
        description="View and manage system alerts"
        icon={Bell}
      />

      <div className="p-6">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Alerts
            </h2>
            <div className="flex items-center gap-2">
              <select className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg">
                <option>All Severities</option>
                <option>Critical</option>
                <option>Warning</option>
                <option>Info</option>
              </select>
              <select className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg">
                <option>Last 24 hours</option>
                <option>Last 7 days</option>
                <option>Last 30 days</option>
              </select>
            </div>
          </div>

          {alerts.length === 0 ? (
            <div className="p-12 text-center">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Alerts</h3>
              <p className="text-gray-500">All systems are operating normally.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {alerts.map((alert, i) => (
                <div key={i} className="p-4 hover:bg-gray-50">
                  {/* Alert item */}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}

export default AlertsPage;
