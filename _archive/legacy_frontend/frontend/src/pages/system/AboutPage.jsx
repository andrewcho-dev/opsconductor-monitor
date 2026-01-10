import React from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { Info, ExternalLink, Github, Book, Mail, Server, Database, Activity } from 'lucide-react';

export function AboutPage() {
  return (
    <PageLayout module="system">
      <PageHeader
        title="About"
        description="System information and technical details"
        icon={Info}
      />

      <div className="p-6 space-y-6 max-w-4xl">
        {/* Version Info */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center gap-4 mb-6">
            <img 
              src="/badge-dark.svg" 
              alt="OpsConductor" 
              className="w-16 h-16"
            />
            <div>
              <h2 className="text-2xl font-bold text-gray-900">OpsConductor Monitor</h2>
              <p className="text-gray-500">Enterprise Network Monitoring & Automation Platform</p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-gray-500">Version</div>
              <div className="font-semibold text-gray-900">2.0.0</div>
            </div>
            <div>
              <div className="text-gray-500">Build Date</div>
              <div className="font-semibold text-gray-900">January 4, 2026</div>
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

        {/* System Architecture */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Server className="w-5 h-5" />
            System Architecture
          </h3>
          <div className="space-y-4 text-sm">
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-2">Backend Services</h4>
              <ul className="space-y-1 text-blue-700">
                <li>• FastAPI REST API server on port 5000</li>
                <li>• Gunicorn WSGI server (production)</li>
                <li>• Celery distributed task queue</li>
                <li>• Celery Beat scheduler</li>
              </ul>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <h4 className="font-semibold text-green-900 mb-2">Data Layer</h4>
              <ul className="space-y-1 text-green-700">
                <li>• PostgreSQL primary database</li>
                <li>• Redis for caching and message broker</li>
                <li>• Database-driven SNMP MIB mappings</li>
                <li>• Dynamic poller configuration storage</li>
              </ul>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg">
              <h4 className="font-semibold text-purple-900 mb-2">Frontend</h4>
              <ul className="space-y-1 text-purple-700">
                <li>• React 18 with TypeScript</li>
                <li>• Vite build system</li>
                <li>• Tailwind CSS for styling</li>
                <li>• Nginx reverse proxy</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Technology Stack */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Database className="w-5 h-5" />
            Technology Stack
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center text-blue-600 font-bold text-xs">Py</div>
              <div>
                <div className="font-medium text-gray-900">Python 3.11+</div>
                <div className="text-gray-500 text-xs">FastAPI, Gunicorn</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-cyan-100 rounded flex items-center justify-center text-cyan-600 font-bold text-xs">Re</div>
              <div>
                <div className="font-medium text-gray-900">React 18</div>
                <div className="text-gray-500 text-xs">Vite, TypeScript</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-green-100 rounded flex items-center justify-center text-green-600 font-bold text-xs">Ce</div>
              <div>
                <div className="font-medium text-gray-900">Celery 5.x</div>
                <div className="text-gray-500 text-xs">Distributed Tasks</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center text-blue-600 font-bold text-xs">Pg</div>
              <div>
                <div className="font-medium text-gray-900">PostgreSQL 15+</div>
                <div className="text-gray-500 text-xs">Primary Database</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-red-100 rounded flex items-center justify-center text-red-600 font-bold text-xs">Rd</div>
              <div>
                <div className="font-medium text-gray-900">Redis 7.x</div>
                <div className="text-gray-500 text-xs">Cache & Broker</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-orange-100 rounded flex items-center justify-center text-orange-600 font-bold text-xs">Ng</div>
              <div>
                <div className="font-medium text-gray-900">Nginx</div>
                <div className="text-gray-500 text-xs">Reverse Proxy</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-purple-100 rounded flex items-center justify-center text-purple-600 font-bold text-xs">Tw</div>
              <div>
                <div className="font-medium text-gray-900">Tailwind CSS</div>
                <div className="text-gray-500 text-xs">Utility-First CSS</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-yellow-100 rounded flex items-center justify-center text-yellow-600 font-bold text-xs">Sn</div>
              <div>
                <div className="font-medium text-gray-900">pysnmp</div>
                <div className="text-gray-500 text-xs">SNMP Library</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-indigo-100 rounded flex items-center justify-center text-indigo-600 font-bold text-xs">Sd</div>
              <div>
                <div className="font-medium text-gray-900">systemd</div>
                <div className="text-gray-500 text-xs">Service Management</div>
              </div>
            </div>
          </div>
        </div>

        {/* Key Features */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Key Features
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">Network Monitoring</h4>
              <ul className="space-y-1 text-gray-600">
                <li>• SNMP polling and data collection</li>
                <li>• Database-driven MIB mappings</li>
                <li>• Real-time topology visualization</li>
                <li>• Optical power monitoring</li>
              </ul>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">Automation</h4>
              <ul className="space-y-1 text-gray-600">
                <li>• Job scheduling and execution</li>
                <li>• Workflow builder</li>
                <li>• Credential management</li>
                <li>• Device configuration</li>
              </ul>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">Integrations</h4>
              <ul className="space-y-1 text-gray-600">
                <li>• NetBox CMDB sync</li>
                <li>• PRTG monitoring</li>
                <li>• Ciena MCP services</li>
                <li>• REST API access</li>
              </ul>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">Enterprise</h4>
              <ul className="space-y-1 text-gray-600">
                <li>• Role-based access control</li>
                <li>• Audit logging</li>
                <li>• High availability deployment</li>
                <li>• Production-ready security</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Resources */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Resources</h3>
          <div className="space-y-3">
            <a href="/docs" className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <Book className="w-5 h-5 text-blue-600" />
              <div className="flex-1">
                <div className="font-medium text-gray-900">Documentation</div>
                <div className="text-sm text-gray-500">System architecture and API reference</div>
              </div>
              <ExternalLink className="w-4 h-4 text-gray-400" />
            </a>
            <a href="https://github.com/enabledconsultants/opsconductor-monitor" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <Github className="w-5 h-5 text-gray-700" />
              <div className="flex-1">
                <div className="font-medium text-gray-900">Source Code</div>
                <div className="text-sm text-gray-500">GitHub repository</div>
              </div>
              <ExternalLink className="w-4 h-4 text-gray-400" />
            </a>
            <a href="mailto:support@enabledconsultants.com" className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <Mail className="w-5 h-5 text-green-600" />
              <div className="flex-1">
                <div className="font-medium text-gray-900">Support</div>
                <div className="text-sm text-gray-500">Contact Enabled Consultants</div>
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
