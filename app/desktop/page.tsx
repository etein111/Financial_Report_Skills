import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

type DesktopCard = {
  key: string;
  icon: string;
  title: string;
  description: string;
  href: string;
  permissionLabel?: string;
  comingSoon?: boolean;
};

const reportsCards: DesktopCard[] = [
  {
    key: "reports",
    icon: "📝",
    title: "Reports",
    description: "View all reports",
    href: "/coming-soon?feature=reports",
    comingSoon: true,
  },
  {
    key: "new-report",
    icon: "➕",
    title: "New Report",
    description: "Create new report",
    href: "/coming-soon?feature=new-report",
    comingSoon: true,
  },
  {
    key: "review",
    icon: "✅",
    title: "Report Review",
    description: "Review pending reports",
    href: "/coming-soon?feature=report-review",
    permissionLabel: "SA/Admin only",
    comingSoon: true,
  },
  {
    key: "templates",
    icon: "📄",
    title: "Templates",
    description: "Manage report templates",
    href: "/coming-soon?feature=templates",
    comingSoon: true,
  },
];

const dataCards: DesktopCard[] = [
  {
    key: "users",
    icon: "👤",
    title: "User Management",
    description: "Manage system users",
    href: "/users",
    permissionLabel: "Admin only",
    comingSoon: false,
  },
  {
    key: "analyst-info",
    icon: "👥",
    title: "Analyst Info",
    description: "Manage analyst profiles",
    href: "/coming-soon?feature=analyst-info",
    permissionLabel: "Admin only",
    comingSoon: true,
  },
  {
    key: "coverage",
    icon: "🏢",
    title: "Coverage",
    description: "Manage coverage universe",
    href: "/coming-soon?feature=coverage",
    comingSoon: true,
  },
  {
    key: "sectors",
    icon: "🏗️",
    title: "Sectors",
    description: "Manage sector taxonomy",
    href: "/coming-soon?feature=sectors",
    comingSoon: true,
  },
  {
    key: "regions",
    icon: "🌍",
    title: "Regions",
    description: "Manage regions",
    href: "/coming-soon?feature=regions",
    comingSoon: true,
  },
];

export default function DesktopPage() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-white/10 bg-zinc-900/60 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <div className="text-xl font-semibold text-zinc-50">Neolyst</div>

          <a
            href="/login"
            className="rounded-[6px] border border-white/10 bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-100 transition-colors duration-200 hover:bg-zinc-700"
          >
            Logout
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 pt-12 pb-10">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:gap-16">
          <Section title="Reports" cards={reportsCards} />
          <Section title="Data Management" cards={dataCards} />
        </div>
      </main>
    </div>
  );
}

function Section({ title, cards }: { title: string; cards: DesktopCard[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-base font-medium text-zinc-200">{title}</h2>
      <div className="flex flex-col gap-4">
        {cards.map((c) => (
          <a
            key={c.key}
            href={c.href}
            target="_blank"
            rel="noopener noreferrer"
            className="block"
          >
            <Card className="flex items-center gap-4 px-5 py-4">
              <div className="text-[28px] leading-none">{c.icon}</div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium text-zinc-100">{c.title}</div>
                <div className="mt-0.5 text-xs text-zinc-400">{c.description}</div>
              </div>
              <div className="flex flex-shrink-0 flex-col items-end gap-1.5">
                {c.permissionLabel ? (
                  <Badge tone="zinc">{c.permissionLabel}</Badge>
                ) : null}
                {c.comingSoon ? <Badge tone="blue">Coming Soon</Badge> : null}
              </div>
            </Card>
          </a>
        ))}
      </div>
    </section>
  );
}

