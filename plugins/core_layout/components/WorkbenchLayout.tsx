/** @jsxImportSource @emotion/react */
import { css } from '@emotion/react';
import React from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import ViewRenderer from './ViewRenderer';

// 使用 Emotion 定义样式
const workbenchStyle = css`
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  background-color: #1f2937; // bg-gray-800
  color: #d1d5db; // text-gray-200
  font-family: sans-serif;
`;

const headerStyle = css`
  height: 2rem; /* h-8 */
  background-color: #111827; /* bg-gray-900 */
  flex-shrink: 0;
`;

const mainStyle = css`
  flex-grow: 1;
  min-height: 0;
`;

const panelStyle = css`
  background-color: #374151; /* bg-gray-700 */
`;

const resizeHandleStyle = css`
  background-color: #111827; /* bg-gray-900 */
  transition: background-color 0.2s;
  &[data-resize-handle-state="hover"],
  &[data-resize-handle-state="drag"] {
    background-color: #3b82f6; /* hover:bg-blue-500 */
  }
`;

const footerStyle = css`
  height: 1.5rem; /* h-6 */
  background-color: #2563eb; /* bg-blue-600 */
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem; /* px-4 */
  font-size: 0.75rem; /* text-xs */
  color: white;
`;

// 组件定义
export default function WorkbenchLayout() {
  return (
    <div css={workbenchStyle}>
      <header css={headerStyle}>
        <ViewRenderer contributionPoint="workbench.titlebar" />
      </header>

      <main css={mainStyle}>
        <PanelGroup direction="horizontal">
          <Panel defaultSize={20} minSize={15}>
            {/* 你可以直接在 ViewRenderer 上写 css prop */}
            <ViewRenderer 
              contributionPoint="workbench.sidebar" 
              css={css`padding: 0.5rem; display: flex; flex-direction: column; gap: 1rem; flex-grow: 1;`} 
            />
          </Panel>
          <PanelResizeHandle css={resizeHandleStyle} style={{ width: '4px' }} />
          
          <Panel>
            <PanelGroup direction="vertical">
              <Panel defaultSize={75} minSize={50} css={panelStyle}>
                <ViewRenderer contributionPoint="workbench.main.container">
                  <div css={css`display: flex; align-items: center; justify-content: center; height: 100%; color: #6b7280;`}>
                    <p>Main Content Area</p>
                  </div>
                </ViewRenderer>
              </Panel>
              <PanelResizeHandle css={resizeHandleStyle} style={{ height: '4px' }}/>
              <Panel defaultSize={25} minSize={10}>
                <ViewRenderer contributionPoint="workbench.panel.container">
                  <div css={css`padding: 0.5rem; color: #6b7280;`}>
                    <p>Panel Area (e.g., Console, Terminal)</p>
                  </div>
                </ViewRenderer>
              </Panel>
            </PanelGroup>
          </Panel>
        </PanelGroup>
      </main>
      
      <footer css={footerStyle}>
        <div css={css`display: flex; align-items: center; gap: 1rem;`}>
            <ViewRenderer contributionPoint="workbench.statusbar.left" />
        </div>
        <div css={css`display: flex; align-items: center; gap: 1rem;`}>
            <ViewRenderer contributionPoint="workbench.statusbar.right" />
        </div>
      </footer>
    </div>
  );
}
