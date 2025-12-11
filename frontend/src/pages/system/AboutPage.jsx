import React from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { Info, ExternalLink, Github, Book, Mail } from 'lucide-react';

export function AboutPage() {
  return (
    <PageLayout module="system">
      <PageHeader
        title="About"
        description="Version information and documentation"
        icon={Info}
      />

      <div className="p-6 space-y-6 max-w-3xl">
        {/* Version Info */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-16 h-16 bg-blue-600 rounded-xl flex items-center justify-center">
              <span className="text-white text-2xl font-bold">OC</span>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">OpsConductor Monitor</h2>
              <p className="text-gray-500">Network Monitoring & Automation Platform</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-500">Version</div>
              <div className="font-semibold text-gray-900">1.0.0</div>
            </div>
            <div>
              <div className="text-gray-500">Build Date</div>
              <div className="font-semibold text-gray-900">December 10, 2025</div>
            </div>
            <div>
              <div className="text-gray-500">License</div>
              <div className="font-semibold text-gray-900">Proprietary</div>
            </div>
            <div>
              <div className="text-gray-500">Environment</div>
              <div className="font-semibold text-gray-900">Production</div>
            </div>
          </div>
        </div>

        {/* Tech Stack */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Technology Stack</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center text-blue-600 font-bold text-xs">Py</div>
              <div>
                <div className="font-medium text-gray-900">Python / Flask</div>
                <div className="text-gray-500 text-xs">Backend API</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-cyan-100 rounded flex items-center justify-center text-cyan-600 font-bold text-xs">Re</div>
              <div>
                <div className="font-medium text-gray-900">React / Vite</div>
                <div className="text-gray-500 text-xs">Frontend UI</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-green-100 rounded flex items-center justify-center text-green-600 font-bold text-xs">Ce</div>
              <div>
                <div className="font-medium text-gray-900">Celery</div>
                <div className="text-gray-500 text-xs">Task Queue</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center text-blue-600 font-bold text-xs">Pg</div>
              <div>
                <div className="font-medium text-gray-900">PostgreSQL</div>
                <div className="text-gray-500 text-xs">Database</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-red-100 rounded flex items-center justify-center text-red-600 font-bold text-xs">Rd</div>
              <div>
                <div className="font-medium text-gray-900">Redis</div>
                <div className="text-gray-500 text-xs">Message Broker</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-purple-100 rounded flex items-center justify-center text-purple-600 font-bold text-xs">Tw</div>
              <div>
                <div className="font-medium text-gray-900">Tailwind CSS</div>
                <div className="text-gray-500 text-xs">Styling</div>
              </div>
            </div>
          </div>
        </div>

        {/* Links */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Resources</h3>
          <div className="space-y-3">
            <a href="#" className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <Book className="w-5 h-5 text-blue-600" />
              <div className="flex-1">
                <div className="font-medium text-gray-900">Documentation</div>
                <div className="text-sm text-gray-500">User guides and API reference</div>
              </div>
              <ExternalLink className="w-4 h-4 text-gray-400" />
            </a>
            <a href="#" className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <Github className="w-5 h-5 text-gray-700" />
              <div className="flex-1">
                <div className="font-medium text-gray-900">Source Code</div>
                <div className="text-sm text-gray-500">GitHub repository</div>
              </div>
              <ExternalLink className="w-4 h-4 text-gray-400" />
            </a>
            <a href="#" className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <Mail className="w-5 h-5 text-green-600" />
              <div className="flex-1">
                <div className="font-medium text-gray-900">Support</div>
                <div className="text-sm text-gray-500">Contact the development team</div>
              </div>
              <ExternalLink className="w-4 h-4 text-gray-400" />
            </a>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}

export default AboutPage;
