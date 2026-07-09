import { PageHeader } from "../../components/PageHeader";

export function AssetsPage() {
  return (
    <section className="page-stack">
      <PageHeader
        title="Assets"
        description="Generated images and videos will collect here for reuse."
      />
      <div className="empty-panel">No generated assets yet.</div>
    </section>
  );
}

