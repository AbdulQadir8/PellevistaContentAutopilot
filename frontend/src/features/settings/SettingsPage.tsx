import { PageHeader } from "../../components/PageHeader";

export function SettingsPage() {
  return (
    <section className="page-stack">
      <PageHeader
        title="Settings"
        description="Connections, brand rules, and publishing preferences will live here."
      />
      <div className="settings-list">
        <label>
          Brand voice
          <input value="Polished, confident, direct" readOnly />
        </label>
        <label>
          Default region
          <input value="United States" readOnly />
        </label>
      </div>
    </section>
  );
}

