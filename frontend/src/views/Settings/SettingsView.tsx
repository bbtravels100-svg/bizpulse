import React, { useState } from 'react';
import { ViewContainer } from '../../components/layout/ViewContainer';
import { BusinessProfileCard } from './BusinessProfileCard';
import { UserProfileCard } from './UserProfileCard';
import { AiPreferencesCard } from './AiPreferencesCard';
import { NotificationsCard } from './NotificationsCard';
import { SystemStatusCard } from './SystemStatusCard';
import { AboutBizPulseCard } from './AboutBizPulseCard';

type SettingsTab = 'all' | 'profile' | 'ai' | 'notifications' | 'system' | 'about';

export const SettingsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('all');
  const [detectedModel, setDetectedModel] = useState<string>('gemini-3.1-flash-lite');

  const tabs: { id: SettingsTab; label: string; icon: string }[] = [
    { id: 'all', label: 'All Settings', icon: '⚙️' },
    { id: 'profile', label: 'Organization & Profile', icon: '🏢' },
    { id: 'ai', label: 'AI Assistant', icon: '🤖' },
    { id: 'notifications', label: 'Notifications', icon: '🔔' },
    { id: 'system', label: 'System Health', icon: '⚡' },
    { id: 'about', label: 'About', icon: 'ℹ️' },
  ];

  return (
    <ViewContainer
      title="Settings Centre"
      subtitle="Organization profile, AI assistant tuning, notification preferences, and real-time system diagnostics."
    >
      {/* Category Navigation Bar */}
      <div
        style={{
          display: 'flex',
          gap: '0.5rem',
          overflowX: 'auto',
          paddingBottom: '0.5rem',
          marginBottom: '1.5rem',
          borderBottom: '1px solid var(--bp-border)',
        }}
      >
        {tabs.map((t) => {
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                padding: '0.5rem 0.95rem',
                borderRadius: '6px',
                border: 'none',
                background: isActive ? 'var(--bp-purple)' : '#FFFFFF',
                color: isActive ? '#FFFFFF' : 'var(--bp-navy)',
                fontWeight: isActive ? 700 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer',
                boxShadow: isActive ? '0 2px 4px rgba(88, 24, 240, 0.2)' : 'none',
                transition: 'all 0.15s ease',
                whiteSpace: 'nowrap',
              }}
            >
              <span>{t.icon}</span>
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* Content Sections */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {(activeTab === 'all' || activeTab === 'profile') && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' }}>
            <BusinessProfileCard />
            <UserProfileCard />
          </div>
        )}

        {(activeTab === 'all' || activeTab === 'ai') && (
          <AiPreferencesCard configuredModel={detectedModel} />
        )}

        {(activeTab === 'all' || activeTab === 'notifications') && (
          <NotificationsCard />
        )}

        {(activeTab === 'all' || activeTab === 'system') && (
          <SystemStatusCard onModelLoaded={(m) => setDetectedModel(m)} />
        )}

        {(activeTab === 'all' || activeTab === 'about') && (
          <AboutBizPulseCard />
        )}
      </div>
    </ViewContainer>
  );
};
