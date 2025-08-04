import React from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import ViewRenderer from './ViewRenderer';

export default function WorkbenchLayout() {
  return (
    <div className="flex flex-col h-screen w-screen bg-gray-800 text-gray-200 font-sans">
      {/* 标题栏区域 */}
      <header className="h-8 bg-gray-900 flex-shrink-0">
        <ViewRenderer contributionPoint="workbench.titlebar" />
      </header>

      {/* 主工作区 */}
      <main className="flex-grow min-h-0">
        <PanelGroup direction="horizontal">
          {/* 侧边栏 */}
          <Panel defaultSize={20} minSize={15} className="bg-gray-800 flex flex-col">
              <ViewRenderer contributionPoint="workbench.sidebar" className="p-2 space-y-4 flex-grow" />
          </Panel>
          <PanelResizeHandle className="w-1 bg-gray-900 hover:bg-blue-500 transition-colors" />
          
          {/* 主内容区 */}
          <Panel>
            <PanelGroup direction="vertical">
              <Panel defaultSize={75} minSize={50} className="bg-gray-700">
                <ViewRenderer contributionPoint="workbench.main.container">
                  <div className="flex items-center justify-center h-full text-gray-500">
                    <p>Main Content Area</p>
                  </div>
                </ViewRenderer>
              </Panel>
              <PanelResizeHandle className="h-1 bg-gray-900 hover:bg-blue-500 transition-colors" />
              <Panel defaultSize={25} minSize={10} className="bg-gray-800">
                <ViewRenderer contributionPoint="workbench.panel.container">
                  <div className="p-2 text-gray-500">
                    <p>Panel Area (e.g., Console, Terminal)</p>
                  </div>
                </ViewRenderer>
              </Panel>
            </PanelGroup>
          </Panel>
        </PanelGroup>
      </main>
      
      {/* 状态栏 */}
      <footer className="h-6 bg-blue-600 flex-shrink-0 flex items-center justify-between px-4 text-xs text-white">
        <div className="flex items-center space-x-4">
            <ViewRenderer contributionPoint="workbench.statusbar.left" />
        </div>
        <div className="flex items-center space-x-4">
            <ViewRenderer contributionPoint="workbench.statusbar.right" />
        </div>
      </footer>
    </div>
  );
}