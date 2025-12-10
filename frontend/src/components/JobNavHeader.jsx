import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, CalendarClock, Settings, Activity } from 'lucide-react';

const JobNavHeader = ({ active }) => {
  const navigate = useNavigate();

  const linkClasses = (key) =>
    [
      'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors border',
      active === key
        ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
        : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50',
    ].join(' ');

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <button
        onClick={() => navigate('/')} 
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 text-sm border border-gray-300"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Main</span>
      </button>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/scheduler')}
          className={linkClasses('scheduler')}
        >
          <CalendarClock className="w-4 h-4" />
          <span>Scheduler</span>
        </button>
        <button
          type="button"
          onClick={() => navigate('/job-definitions')}
          className={linkClasses('definitions')}
        >
          <Settings className="w-4 h-4" />
          <span>Job Definitions</span>
        </button>
        <button
          type="button"
          onClick={() => navigate('/scheduler')}
          className={linkClasses('scheduler')}
        >
          <Activity className="w-4 h-4" />
          <span>Scheduler</span>
        </button>
      </div>
    </div>
  );
};

export default JobNavHeader;
