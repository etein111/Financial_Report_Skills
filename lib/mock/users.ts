export type UserRole = "admin" | "sa" | "analyst";
export type UserStatus = "active" | "banned";

export type MockUser = {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  status: UserStatus;
  createdAt: string; // ISO
};

export function makeMockUsers(): MockUser[] {
  const names = [
    "Alex Chen",
    "Bella Zhang",
    "Chris Wang",
    "Daisy Li",
    "Ethan Liu",
    "Fiona Xu",
    "Grace Huang",
    "Henry Zhao",
    "Iris Lin",
    "Jason Wu",
    "Kelly Sun",
    "Leo Guo",
  ];

  const roles: UserRole[] = ["analyst", "analyst", "sa", "analyst", "admin"];
  const users: MockUser[] = [];

  for (let i = 0; i < 42; i += 1) {
    const n = names[i % names.length];
    const role = roles[i % roles.length];
    const status: UserStatus = i % 13 === 0 ? "banned" : "active";
    const dayOffset = 120 - i;
    const createdAt = new Date(Date.now() - dayOffset * 24 * 60 * 60 * 1000).toISOString();

    const first = n.split(" ")[0].toLowerCase();
    users.push({
      id: `u_${i + 1}`,
      email: `${first}.${i + 1}@example.com`,
      name: n,
      role,
      status,
      createdAt,
    });
  }

  // Newest first
  return users.sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
}

export function filterUsers(users: MockUser[], query: string): MockUser[] {
  const q = query.trim().toLowerCase();
  if (!q) return users;
  return users.filter((u) => {
    return u.email.toLowerCase().includes(q) || u.name.toLowerCase().includes(q);
  });
}

export function paginate<T>(items: T[], page: number, pageSize: number) {
  const total = items.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const start = (safePage - 1) * pageSize;
  const end = start + pageSize;
  return {
    total,
    totalPages,
    page: safePage,
    pageSize,
    items: items.slice(start, end),
  };
}

