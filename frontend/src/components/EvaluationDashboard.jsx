import { useState, useEffect } from "react";
import {
  BarChart3,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Play,
  FileText,
  AlertTriangle,
  Search,
} from "lucide-react";
import axios from "axios";
import { useToast } from "./Toast";

const API = import.meta.env.VITE_API_URL || "http://localhost:5000";

function MetricCard({ label, value, format, icon: Icon, color, subtitle }) {
  const fmt = format === "percent" ? `${(value * 100).toFixed(1)}%`
    : format === "decimal" ? value.toFixed(4)
    : value;

  const textColor = value > 0.8 ? "text-green-600"
    : value > 0.6 ? "text-yellow-600"
    : "text-red-600";

  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-[#6B7280] uppercase tracking-wide">{label}</span>
        <Icon className={`w-4 h-4 ${color || "text-[#6B7280]"}`} />
      </div>
      <div className={`text-2xl font-bold ${textColor}`}>{fmt}</div>
      {subtitle && <p className="text-xs text-[#9CA3AF] mt-1">{subtitle}</p>}
    </div>
  );
}

function CategoryBreakdown({ results }) {
  const categories = {};
  results?.forEach((r) => {
    const cat = r.category || "Uncategorized";
    if (!categories[cat]) categories[cat] = { count: 0, faithfulness: 0, recall: 0 };
    categories[cat].count += 1;
    categories[cat].faithfulness += r.faithfulness || 0;
    categories[cat].recall += r.retrieval_recall_5 || 0;
  });

  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-[#111827] mb-3">Per-Category Breakdown</h3>
      <div className="space-y-2">
        {Object.entries(categories).map(([cat, data]) => (
          <div key={cat} className="flex items-center gap-3 text-xs">
            <span className="w-20 font-medium text-[#374151] truncate">{cat}</span>
            <div className="flex-1 flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="text-[#6B7280]">Recall@5:</span>
                <span className="font-semibold text-[#111827]">
                  {((data.recall / data.count) * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-[#6B7280]">Faithfulness:</span>
                <span className="font-semibold text-[#111827]">
                  {((data.faithfulness / data.count) * 100).toFixed(1)}%
                </span>
              </div>
              <span className="text-[#9CA3AF]">({data.count} questions)</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FailedQuestions({ results }) {
  const failed = results?.filter(
    (r) => (r.retrieval_hit_rate || 0) < 1 || (r.error && r.error !== "")
  ) || [];

  if (failed.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-red-200 p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-4 h-4 text-red-500" />
        <h3 className="text-sm font-semibold text-red-700">
          {failed.length} Question{failed.length > 1 ? "s" : ""} Need Attention
        </h3>
      </div>
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {failed.slice(0, 5).map((r, i) => (
          <div key={i} className="flex items-start gap-2 text-xs text-[#6B7280]">
            <span className="text-red-400 mt-0.5 shrink-0">•</span>
            <span className="line-clamp-1">{r.question || "Unknown"}</span>
            {r.error && <span className="text-red-500 shrink-0">({r.error})</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

function RunHistory({ runs, onSelect }) {
  if (!runs || runs.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-[#111827] mb-3">Past Evaluation Runs</h3>
      <div className="space-y-1 max-h-48 overflow-y-auto">
        {runs.slice(0, 10).map((run) => (
          <button
            key={run.id}
            onClick={() => onSelect(run.id)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-50 text-xs text-left transition-colors"
          >
            <div className="flex items-center gap-2">
              <BarChart3 className="w-3.5 h-3.5 text-[#6B7280]" />
              <span className="text-[#374151]">
                {new Date(run.run_date).toLocaleDateString()} {new Date(run.run_date).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
            <div className="flex items-center gap-3 text-[#6B7280]">
              <span>R@5: {((run.overall_recall_5 || 0) * 100).toFixed(0)}%</span>
              <span>F: {((run.overall_faithfulness || 0) * 100).toFixed(0)}%</span>
              <span className="text-[#9CA3AF]">{run.num_questions} Q</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function EvaluationDashboard() {
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const { addToast } = useToast();

  const fetchRuns = async () => {
    try {
      const res = await axios.get(`${API}/api/evaluation/runs`);
      const fetched = res.data.runs || [];
      setRuns(fetched);
      if (fetched.length > 0 && !selectedRun) {
        setSelectedRun(fetched[0]);
      }
    } catch {
      setRuns([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const handleSelectRun = async (runId) => {
    try {
      const res = await axios.get(`${API}/api/evaluation/runs/${runId}`);
      setSelectedRun(res.data.run);
    } catch {
      addToast("Failed to load run details", "error");
    }
  };

  const handleRunEvaluation = async () => {
    setRunning(true);
    try {
      await axios.post(`${API}/api/evaluation/run`);
      addToast("Evaluation started — check back in a moment", "success");
      setTimeout(() => {
        fetchRuns();
        setRunning(false);
      }, 5000);
    } catch (err) {
      addToast(err.response?.data?.error || "Failed to start evaluation", "error");
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-[32px] font-bold text-[#111827] mb-6">Evaluation Dashboard</h1>
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-[#2563EB] border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  const results = selectedRun?.results || [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[32px] font-bold text-[#111827]">Evaluation Dashboard</h1>
          <p className="text-[#6B7280] mt-1">
            Measure retrieval quality, answer faithfulness, and overall RAG performance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchRuns}
            className="flex items-center gap-2 px-4 py-2.5 border border-[#E5E7EB] rounded-lg text-sm font-medium text-[#374151] hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={handleRunEvaluation}
            disabled={running}
            className="flex items-center gap-2 bg-[#2563EB] text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            {running ? "Running..." : "Run Evaluation"}
          </button>
        </div>
      </div>

      {/* No data state */}
      {!selectedRun && (
        <div className="text-center py-20">
          <BarChart3 className="w-16 h-16 text-[#E5E7EB] mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-[#111827] mb-2">No evaluation data yet</h3>
          <p className="text-sm text-[#6B7280] max-w-md mx-auto mb-6">
            Run your first evaluation to measure retrieval quality, answer faithfulness, and groundedness.
          </p>
          <button
            onClick={handleRunEvaluation}
            disabled={running}
            className="inline-flex items-center gap-2 bg-[#2563EB] text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            Start First Evaluation
          </button>
        </div>
      )}

      {/* Metrics Grid */}
      {selectedRun && (
        <>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <MetricCard
              label="Recall@5"
              value={selectedRun.overall_recall_5 || 0}
              format="percent"
              icon={Search}
              color="text-blue-500"
              subtitle="Retrieved relevant docs"
            />
            <MetricCard
              label="Precision@5"
              value={selectedRun.overall_precision_5 || 0}
              format="percent"
              icon={CheckCircle2}
              color="text-green-500"
              subtitle="Retrieved docs were relevant"
            />
            <MetricCard
              label="MRR"
              value={selectedRun.overall_mrr || 0}
              format="decimal"
              icon={TrendingUp}
              color="text-purple-500"
              subtitle="Mean Reciprocal Rank"
            />
            <MetricCard
              label="Hit Rate"
              value={selectedRun.overall_hit_rate || 0}
              format="percent"
              icon={CheckCircle2}
              color="text-emerald-500"
              subtitle="At least 1 relevant doc"
            />
          </div>

          <div className="grid grid-cols-4 gap-4 mb-6">
            <MetricCard
              label="Faithfulness"
              value={selectedRun.overall_faithfulness || 0}
              format="percent"
              icon={FileText}
              color="text-indigo-500"
              subtitle="Answer matches context"
            />
            <MetricCard
              label="Relevance"
              value={selectedRun.overall_relevance || 0}
              format="percent"
              icon={BarChart3}
              color="text-teal-500"
              subtitle="Answer addresses question"
            />
            <MetricCard
              label="Groundedness"
              value={selectedRun.overall_groundedness || 0}
              format="percent"
              icon={CheckCircle2}
              color="text-cyan-500"
              subtitle="Claims supported by context"
            />
            <MetricCard
              label="Avg Latency"
              value={selectedRun.avg_latency_seconds || 0}
              format="raw"
              icon={Clock}
              color="text-orange-500"
              subtitle={`${selectedRun.num_questions || 0} questions`}
            />
          </div>

          {/* Category Breakdown & Failed Questions */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <CategoryBreakdown results={results} />
            <FailedQuestions results={results} />
          </div>

          {/* Run History */}
          <RunHistory runs={runs} onSelect={handleSelectRun} />
        </>
      )}
    </div>
  );
}
