'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { StatusDot } from '@/components/agents/AgentBadge';
import { useResearchStore } from '@/store';
import { Rocket, Compass, BarChart3, Settings } from 'lucide-react';

export function Header() {
  const pathname = usePathname();
  const { currentSession, wsConnected, activeAgent } = useResearchStore();

  const navItems = [
    { href: '/', label: 'Launchpad', icon: Rocket },
    { href: '/mission', label: 'Mission Control', icon: Compass },
    { href: '/discovery', label: 'Discovery Deck', icon: BarChart3 },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-deep-space/80 backdrop-blur-xl">
      <div className="container flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-6">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center transform group-hover:scale-110 transition-transform">
              <Compass className="w-5 h-5 text-white" />
            </div>
            <span className="font-display text-lg font-semibold text-gradient hidden sm:inline">
              Co-Scientist
            </span>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link key={item.href} href={item.href}>
                  <Button
                    variant={isActive ? 'neon' : 'ghost'}
                    size="sm"
                    className={cn(
                      'gap-2',
                      isActive && 'shadow-neon-cyan'
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </Button>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Status & Actions */}
        <div className="flex items-center gap-4">
          {/* Connection Status */}
          {currentSession && (
            <div className="flex items-center gap-2 text-sm">
              <StatusDot status={wsConnected ? 'active' : 'pending'} />
              <span className="text-muted-foreground hidden sm:inline">
                {wsConnected ? 'Connected' : 'Connecting...'}
              </span>
              {activeAgent && (
                <span className="text-cyan-400 font-medium">
                  {activeAgent}
                </span>
              )}
            </div>
          )}

          {/* Settings */}
          <Button variant="ghost" size="icon">
            <Settings className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
