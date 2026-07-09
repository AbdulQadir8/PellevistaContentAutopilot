import { useQuery } from "@tanstack/react-query";

import { fetchReviewQueue } from "../../api/fakeApi";
import { PageHeader } from "../../components/PageHeader";

const actions = ["Approve", "Reject", "Regenerate", "Schedule"];

export function ReviewQueuePage() {
  const { data: queue = [], isLoading } = useQuery({
    queryKey: ["review-queue"],
    queryFn: fetchReviewQueue,
  });

  return (
    <section className="page-stack">
      <PageHeader
        title="Review Queue"
        description="Approve, reject, regenerate, or schedule generated content before it leaves the system."
      />

      <div className="review-list">
        {isLoading ? <p>Loading review items...</p> : null}
        {queue.map((item) => (
          <article className="review-item" key={item.id}>
            <div className="reference-block">
              <img src={item.productImageUrl} alt="" />
              <div>
                <span>Product reference</span>
                <strong>{item.productTitle}</strong>
              </div>
            </div>

            <div className="generated-placeholder">
              <span>{item.generatedAssetLabel}</span>
            </div>

            <div className="caption-block">
              <span>{item.platform}</span>
              <p>{item.caption}</p>
              <small>{item.status}</small>
            </div>

            <div className="review-actions">
              {actions.map((action) => (
                <button key={action} type="button">
                  {action}
                </button>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

