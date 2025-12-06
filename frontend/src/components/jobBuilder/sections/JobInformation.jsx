import React from 'react';

export const JobInformation = ({ currentJob, setCurrentJob }) => (
  <div className="bg-white rounded shadow p-3 mb-2">
    <h2 className="text-lg font-bold mb-2">JOB INFORMATION</h2>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div>
        <label className="block text-xs font-medium mb-1">Job ID</label>
        <input
          type="text"
          value={currentJob.job_id}
          onChange={(e) => setCurrentJob((prev) => ({ ...prev, job_id: e.target.value }))}
          className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
        />
      </div>
      <div>
        <label className="block text-xs font-medium mb-1">Name</label>
        <input
          type="text"
          value={currentJob.name}
          onChange={(e) => setCurrentJob((prev) => ({ ...prev, name: e.target.value }))}
          className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
        />
      </div>
      <div>
        <label className="block text-xs font-medium mb-1">Description</label>
        <input
          type="text"
          value={currentJob.description}
          onChange={(e) => setCurrentJob((prev) => ({ ...prev, description: e.target.value }))}
          className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
          placeholder="Describe what this job does"
        />
      </div>
    </div>
  </div>
);
