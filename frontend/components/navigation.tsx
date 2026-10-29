"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, CalendarRange, BookOpen, Activity } from "lucide-react";

const links = [
  { href: "/", label: "Overview", Icon: LayoutDashboard },
  { href: "/weeks/", label: "Weeks", Icon: CalendarRange },
  { href: "/learning/", label: "Learning", Icon: BookOpen },
  { href: "/operations/", label: "Status", Icon: Activity },
];

export default function Navigation({ mobile = false }: { mobile?: boolean }) {
  const pathname = usePathname();
  const currentPath = `${pathname.replace(/\/$/, "")}/`;

  return (
    <nav
      className={mobile ? "mobile-nav" : undefined}
      aria-label={mobile ? "Mobile navigation" : "Main navigation"}
    >
      {links.map(({ href, label, Icon }) => {
        const active =
          href === "/" ? currentPath === "/" : currentPath.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            title={label}
          >
            <Icon size={18} aria-hidden="true" />
            <span className="nav-text">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
