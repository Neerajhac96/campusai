import { useEffect, useState } from "react";
import { getAnalytics } from "../api/client";

const AnalyticsDashboard = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const data = await getAnalytics();
      setAnalytics(data);
    } catch (error) {
      window.alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  if (loading && !analytics) {
    return <p className="text-sm text-gray-500">Loading analytics...</p>;
  }

  if (!analytics) {
    return null;
  }

  const totalLang = (analytics.language_breakdown.hindi || 0) + (analytics.language_breakdown.english || 0);
  const hindiPercent = totalLang ? Math.round(((analytics.language_breakdown.hindi || 0) / totalLang) * 100) : 0;
  const englishPercent = totalLang ? 100 - hindiPercent : 0;

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Total Queries (Month)</p>
          <p className="mt-1 text-2xl font-bold text-wa-dark">{analytics.total_queries_month}</p>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Resolution Rate</p>
          <p className="mt-1 text-2xl font-bold text-wa-dark">{analytics.resolution_rate}%</p>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Language Split</p>
          <p className="mt-1 text-lg font-semibold text-gray-800">
            Hindi {hindiPercent}% / English {englishPercent}%
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700">Top 10 Questions</h3>
          <ul className="mt-3 space-y-2">
            {analytics.top_questions.map((item) => (
              <li key={item.question} className="rounded-md bg-gray-50 px-3 py-2 text-sm">
                <span className="font-semibold text-gray-800">{item.count}x</span> {item.question}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-xl bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700">Queries by Category</h3>
          <div className="mt-3 space-y-2">
            {analytics.category_breakdown.map((item) => (
              <div key={item.category}>
                <div className="mb-1 flex justify-between text-xs text-gray-600">
                  <span className="capitalize">{item.category}</span>
                  <span>{item.count}</span>
                </div>
                <div className="h-2 w-full rounded bg-gray-100">
                  <div
                    className="h-2 rounded bg-wa-green"
                    style={{
                      width: `${Math.min(100, (item.count / Math.max(1, analytics.total_queries_month)) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
            {analytics.category_breakdown.length === 0 && (
              <p className="text-sm text-gray-500">No category usage data yet.</p>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700">Queries per Day (Last 30 Days)</h3>
        <div className="mt-4 flex h-44 items-end gap-2 overflow-x-auto">
          {analytics.queries_per_day.map((point) => {
            const max = Math.max(1, ...analytics.queries_per_day.map((entry) => entry.count));
            const height = Math.max(8, (point.count / max) * 160);
            return (
              <div key={point.day} className="flex min-w-8 flex-col items-center gap-1">
                <div title={`${point.day}: ${point.count}`} className="w-7 rounded-t bg-wa-dark" style={{ height }} />
                <span className="text-[10px] text-gray-500">{point.day.slice(5)}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
