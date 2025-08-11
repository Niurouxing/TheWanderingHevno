// plugins/core_layout/src/context/LayoutContext.jsx
import React, { createContext, useState, useContext, useMemo } from 'react';
import { ContributionRegistry } from '../services/ContributionRegistry';

const LayoutContext = createContext(null);

export function LayoutProvider({ children, services }) {
  // 使用 useMemo 确保 registry 只被实例化一次
  const contributionRegistry = useMemo(() => {
    const manifestProvider = services.get('manifestProvider');
    return new ContributionRegistry(manifestProvider);
  }, [services]);

  const [pages] = useState(() => contributionRegistry.getPageComponents());
  const [activePageId, setActivePageId] = useState(null);
  const [currentSandboxId, setCurrentSandboxId] = useState(null); 

  const value = {
    pages,
    activePageId,
    setActivePageId,
    currentSandboxId,
    setCurrentSandboxId,
    services, // 将平台服务传递下去
  };

  return (
    <LayoutContext.Provider value={value}>
      {children}
    </LayoutContext.Provider>
  );
}

export const useLayout = () => {
  const context = useContext(LayoutContext);
  if (!context) {
    throw new Error('useLayout must be used within a LayoutProvider');
  }
  return context;
};