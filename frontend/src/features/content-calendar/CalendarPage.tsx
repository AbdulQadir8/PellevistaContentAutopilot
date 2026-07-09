import { PageHeader } from "../../components/PageHeader";

export function CalendarPage() {
  return (
    <section className="page-stack">
      <PageHeader
        title="Calendar"
        description="Scheduled posts will appear here once the workflow reaches scheduling."
      />
      <div className="empty-panel">No scheduled posts yet.</div>
    </section>
  );
}

