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
          <div className="flex items-center gap-3">
            <div className="text-xl font-semibold text-zinc-50">Neolyst</div>
            <div className="hidden text-sm text-zinc-400 sm:block">
              Welcome back
            </div>
          </div>

          <a
            href="/login"
            className="rounded-[6px] border border-white/10 bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-100 transition-colors duration-200 hover:bg-zinc-700"
          >
            Logout
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <Section title="Reports" cards={reportsCards} />
        <div className="h-8" />
        <Section title="Data Management" cards={dataCards} />
      </main>
    </div>
  );
}

function Section({ title, cards }: { title: string; cards: DesktopCard[] }) {
  return (
    <section className="space-y-4">
      <h2 className="text-sm font-medium text-zinc-300">{title}</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <a
            key={c.key}
            href={c.href}
            target="_blank"
            rel="noopener noreferrer"
            className="block"
          >
            <Card className="h-full">
              <div className="flex items-start justify-between gap-3">
                <div className="text-[40px] leading-none">{c.icon}</div>
                <div className="flex flex-col items-end gap-2">
                  {c.permissionLabel ? (
                    <Badge tone="zinc">{c.permissionLabel}</Badge>
                  ) : null}
                  {c.comingSoon ? <Badge tone="blue">Coming Soon</Badge> : null}
                </div>
              </div>

              <div className="mt-4 space-y-1">
                <div className="text-sm font-medium text-zinc-100">{c.title}</div>
                <div className="text-xs text-zinc-400">{c.description}</div>
              </div>
            </Card>
          </a>
        ))}
      </div>
    </section>
  );
}

