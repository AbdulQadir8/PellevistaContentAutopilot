import { useQuery } from "@tanstack/react-query";

import { fetchAnalyticsDashboard } from "../../api/fakeApi";
import { PageHeader } from "../../components/PageHeader";

export function AnalyticsPage() {
  const { data: analytics, isLoading } = useQuery({
    queryKey: ["analytics-dashboard"],
    queryFn: fetchAnalyticsDashboard,
  });

  const highlights = analytics
    ? [
        [
          "Best platform",
          analytics.best_platform.label,
          analytics.best_platform.score,
        ],
        ["Best product", analytics.best_product.label, analytics.best_product.score],
        ["Best hook", analytics.best_hook.label, analytics.best_hook.score],
        [
          "Best pillar",
          analytics.best_content_pillar.label,
          analytics.best_content_pillar.score,
        ],
        [
          "Best time",
          analytics.best_posting_time.label,
          analytics.best_posting_time.score,
        ],
        ["Published posts", String(analytics.total_published_posts), null],
        ["Pending collection", String(analytics.pending_collections), null],
      ]
    : [];

  return (
    <section className="page-stack">
      <PageHeader
        title="Analytics"
        description="Track post performance, winning content pillars, and the next workflow action."
      />
      {isLoading ? <div className="empty-panel">Loading analytics...</div> : null}
      {analytics ? (
        <>
          <div className="metric-grid analytics-grid">
            {highlights.map(([label, value, score]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
                {score !== null ? <small>Score {score}</small> : null}
              </div>
            ))}
          </div>

          <div className="analytics-details">
            <article>
              <span>Worst post</span>
              {analytics.worst_post ? (
                <>
                  <strong>{analytics.worst_post.platform}</strong>
                  <p>{analytics.worst_post.caption}</p>
                  <a href={analytics.worst_post.external_post_url}>Open post</a>
                </>
              ) : (
                <p>No published post data yet.</p>
              )}
            </article>

            <article>
              <span>Next action</span>
              <strong>{analytics.next_action}</strong>
              <p>{analytics.total_snapshots} analytics snapshots tracked.</p>
            </article>
          </div>
        </>
      ) : null}
    </section>
  );
}
