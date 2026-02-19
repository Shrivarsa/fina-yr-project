import { useState, useEffect } from 'react';
import { Shield, AlertTriangle, CheckCircle, XCircle, Clock, User, Hash, Activity, LogOut, Zap } from 'lucide-react';
import { useAuth } from './AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export default function SCIPDashboard() {
  const { user, accessToken, logout } = useAuth();
  const [codeContent, setCodeContent] = useState('');
  const [logs, setLogs] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (accessToken) {
      fetchLogs();
      const interval = setInterval(fetchLogs, 3000);
      return () => clearInterval(interval);
    }
  }, [accessToken]);

  const fetchLogs = async () => {
    try {
      const response = await fetch(`${API_URL}/api/logs`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }

      const data = await response.json();
      setLogs(data.logs || []);
    } catch (err) {
      console.error('Error fetching logs:', err);
    }
  };

  const handlePushCommit = async () => {
    if (!codeContent.trim()) {
      setError('Please enter some code content');
      return;
    }

    setError('');
    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_URL}/api/analyze_commit`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code_content: codeContent,
        }),
      });

      const result = await response.json();

      if (response.ok) {
        setCodeContent('');
        fetchLogs();
      } else {
        setError(result.error || 'Failed to analyze commit');
      }
    } catch (err) {
      setError(`Connection error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getRiskColor = (riskScore) => {
    if (riskScore < 50) return 'text-green-400';
    if (riskScore < 75) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getRiskMeterColor = (riskScore) => {
    if (riskScore < 50) return 'from-green-500 to-green-600';
    if (riskScore < 75) return 'from-yellow-500 to-yellow-600';
    return 'from-red-500 to-red-600';
  };

  const getStatusColor = (status) => {
    return status === 'Accepted' ? 'text-green-400' : 'text-red-400';
  };

  const getStatusIcon = (status) => {
    return status === 'Accepted' ? (
      <CheckCircle className="w-5 h-5 text-green-400" />
    ) : (
      <XCircle className="w-5 h-5 text-red-400" />
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-gray-100">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-12">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="bg-blue-600 p-3 rounded-lg">
                <Shield className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                  SCIP Guardian
                </h1>
                <p className="text-gray-400 mt-1">Multi-User Code Security Platform</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3 bg-gray-800 px-4 py-2 rounded-lg border border-gray-700">
                <User className="w-4 h-4 text-blue-400" />
                <span className="text-sm text-gray-300">{user?.username}</span>
              </div>
              <button
                onClick={logout}
                className="flex items-center space-x-2 bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span className="text-sm">Logout</span>
              </button>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-gray-800 rounded-xl shadow-2xl border border-gray-700 p-6">
            <div className="flex items-center space-x-3 mb-6">
              <div className="bg-blue-600 p-2 rounded-lg">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <h2 className="text-2xl font-semibold text-gray-100">Commit Simulator</h2>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Code Content
              </label>
              <textarea
                value={codeContent}
                onChange={(e) => setCodeContent(e.target.value)}
                className="w-full h-56 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-gray-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                placeholder="// Paste your code here to analyze security risks...&#10;function example() {&#10;  return 'Hello World';&#10;}"
              />
            </div>

            {error && (
              <div className="mb-4 bg-red-900 border border-red-700 text-red-200 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              onClick={handlePushCommit}
              disabled={isSubmitting}
              className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 disabled:from-gray-600 disabled:to-gray-700 text-white font-semibold py-2 px-6 rounded-lg transition-all duration-200 flex items-center justify-center space-x-2 shadow-lg"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <Shield className="w-4 h-4" />
                  <span>Push & Analyze</span>
                </>
              )}
            </button>

            <div className="mt-4 p-4 bg-gray-900 rounded-lg border border-gray-700">
              <p className="text-xs text-gray-400 font-semibold mb-2">RISK SCALE</p>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-green-400">Low (0-50%)</span>
                <span className="text-yellow-400">Medium (50-75%)</span>
                <span className="text-red-400">High (75-100%)</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-xl shadow-2xl border border-gray-700 p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="bg-cyan-600 p-2 rounded-lg">
                  <Activity className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-2xl font-semibold text-gray-100">Real-time Audit Log</h2>
              </div>
              <span className="text-sm text-gray-400">{logs.length} commits</span>
            </div>

            <div className="space-y-3 max-h-[600px] overflow-y-auto custom-scrollbar">
              {logs.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No commits analyzed yet</p>
                  <p className="text-sm mt-2">Push your first commit to see results</p>
                </div>
              ) : (
                logs.map((log) => (
                  <div
                    key={log.commit_id}
                    className="bg-gray-900 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors duration-200"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(log.status)}
                        <span className={`font-semibold text-sm ${getStatusColor(log.status)}`}>
                          {log.status}
                        </span>
                      </div>
                      <span className={`text-lg font-bold ${getRiskColor(log.risk_score)}`}>
                        {log.risk_score.toFixed(1)}%
                      </span>
                    </div>

                    <div className="mb-3 w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${getRiskMeterColor(log.risk_score)} transition-all duration-300`}
                        style={{ width: `${Math.min(log.risk_score, 100)}%` }}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="flex items-center space-x-2 text-gray-400">
                        <Hash className="w-3 h-3" />
                        <span className="font-mono text-xs truncate">{log.commit_hash}</span>
                      </div>
                      <div className="flex items-center space-x-2 text-gray-400">
                        <User className="w-3 h-3" />
                        <span className="text-xs truncate">{log.user}</span>
                      </div>
                      <div className="col-span-2 flex items-center space-x-2 text-gray-400">
                        <Clock className="w-3 h-3" />
                        <span className="text-xs">
                          {new Date(log.timestamp).toLocaleDateString()} {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      {log.dlt_tx_hash && (
                        <div className="col-span-2 mt-2 pt-2 border-t border-gray-800">
                          <span className="text-xs text-gray-500">DLT TX: </span>
                          <span className="text-xs font-mono text-cyan-400">{log.dlt_tx_hash}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <footer className="mt-12 text-center text-gray-500 text-sm">
          <p>SCIP Guardian v2.0 | Multi-User Platform | Powered by AI & Blockchain</p>
        </footer>
      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #1f2937;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #4b5563;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #6b7280;
        }
      `}</style>
    </div>
  );
}
