import { useState, useEffect } from 'react';
import {
  Shield,
  CheckCircle,
  XCircle,
  Clock,
  User,
  Hash,
  Activity,
  LogOut,
  Zap,
} from 'lucide-react';
import { useAuth } from './useAuth';

const API_URL = 'http://localhost:5000';

export default function SCIPDashboard() {
  const { user, accessToken,  logout } = useAuth();
  const [codeContent, setCodeContent] = useState('');
  const [logs, setLogs] = useState<Array<{
    commit_id: string;
    commit_hash: string;
    timestamp: string;
    status: string;
    risk_score: number;
  }>>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  // ✅ SAFE POLLING — only runs when token exists
  useEffect(() => {
    if (!accessToken) return;

    const fetchLogs = async () => {
      if (!accessToken) return;

      try {
        const response = await fetch(`${API_URL}/api/logs`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });

        // ❗ Do NOT logout on 401 — prevents redirect loop
        if (response.status === 401) {
          console.warn('Unauthorized – token may be expired');
          return;
        }

        if (!response.ok) {
          throw new Error('Failed to fetch logs');
        }

        const data = await response.json();
        setLogs(data.logs || []);
      } catch (err) {
        console.error('Error fetching logs:', err);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 3000);

    return () => clearInterval(interval);
  }, [accessToken]);

  // 🔒 HARD AUTH GUARD — prevents login → logout loop
  if (!user || !accessToken) {
    return null;
  }

  const handlePushCommit = async () => {
    if (!codeContent.trim()) {
      setError('Please enter some code content');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const response = await fetch(`${API_URL}/api/analyze_commit`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code_content: codeContent,
        }),
      });

      const result = await response.json();

      if (response.ok) {
        setCodeContent('');
      } else {
        setError(result.error || 'Analysis failed');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(`Connection error: ${errorMessage}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getRiskColor = (risk: number) =>
    risk < 50 ? 'text-green-400' : risk < 75 ? 'text-yellow-400' : 'text-red-400';

  const getRiskMeterColor = (risk: number) =>
    risk < 50
      ? 'from-green-500 to-green-600'
      : risk < 75
      ? 'from-yellow-500 to-yellow-600'
      : 'from-red-500 to-red-600';

  const getStatusIcon = (status: string) =>
    status === 'Accepted' ? (
      <CheckCircle className="w-5 h-5 text-green-400" />
    ) : (
      <XCircle className="w-5 h-5 text-red-400" />
    );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-gray-100">
      <div className="container mx-auto px-4 py-8">

        {/* HEADER */}
        <header className="mb-12 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="bg-blue-600 p-3 rounded-lg">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                SCIP Guardian
              </h1>
              <p className="text-gray-400 mt-1">
                Secure Code Integrity Platform
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-gray-800 px-4 py-2 rounded-lg border border-gray-700">
              <User className="w-4 h-4 text-blue-400" />
              <span className="text-sm">{user.username}</span>
            </div>
            <button
              onClick={logout}
              className="flex items-center space-x-2 bg-red-600 hover:bg-red-700 px-3 py-2 rounded-lg"
            >
              <LogOut className="w-4 h-4" />
              <span className="text-sm">Logout</span>
            </button>
          </div>
        </header>

        {/* MAIN GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

          {/* COMMIT PANEL */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center space-x-3 mb-6">
              <Zap className="w-5 h-5 text-cyan-400" />
              <h2 className="text-2xl font-semibold">Commit Simulator</h2>
            </div>

            <textarea
              value={codeContent}
              onChange={(e) => setCodeContent(e.target.value)}
              className="w-full h-56 bg-gray-900 border border-gray-700 rounded-lg p-4 font-mono text-sm"
              placeholder="// Paste code here"
            />

            {error && (
              <div className="mt-3 bg-red-900 border border-red-700 text-red-200 p-3 rounded">
                {error}
              </div>
            )}

            <button
              onClick={handlePushCommit}
              disabled={isSubmitting}
              className="mt-4 w-full bg-gradient-to-r from-blue-600 to-cyan-600 py-2 rounded-lg"
            >
              {isSubmitting ? 'Analyzing…' : 'Push & Analyze'}
            </button>
          </div>

          {/* LOG PANEL */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <Activity className="w-5 h-5 text-cyan-400" />
                <h2 className="text-2xl font-semibold">Audit Log</h2>
              </div>
              <span className="text-sm text-gray-400">{logs.length} commits</span>
            </div>

            <div className="space-y-3 max-h-[600px] overflow-y-auto">
              {logs.length === 0 ? (
                <p className="text-gray-500 text-center">No commits yet</p>
              ) : (
                logs.map((log) => (
                  <div key={log.commit_id} className="bg-gray-900 p-4 rounded-lg">
                    <div className="flex justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(log.status)}
                        <span>{log.status}</span>
                      </div>
                      <span className={`font-bold ${getRiskColor(log.risk_score)}`}>
                        {log.risk_score.toFixed(1)}%
                      </span>
                    </div>

                    <div className="w-full bg-gray-800 h-2 rounded-full mb-2">
                      <div
                        className={`h-2 rounded-full bg-gradient-to-r ${getRiskMeterColor(log.risk_score)}`}
                        style={{ width: `${Math.min(log.risk_score, 100)}%` }}
                      />
                    </div>

                    <div className="text-xs text-gray-400 space-y-1">
                      <div className="flex items-center space-x-2">
                        <Hash className="w-3 h-3" />
                        <span className="font-mono">{log.commit_hash}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Clock className="w-3 h-3" />
                        <span>{new Date(log.timestamp).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <footer className="mt-12 text-center text-gray-500 text-sm">
          SCIP Guardian v2.0 • AI + Blockchain Security
        </footer>
      </div>
    </div>
  );
}
