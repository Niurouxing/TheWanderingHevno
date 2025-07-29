import { useState, useCallback } from 'react';
import ReactFlow, {
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  // 使用 'type' 关键字显式导入类型
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
} from 'reactflow';
import 'reactflow/dist/style.css';
import axios from 'axios';

// MVP阶段的初始节点和边
const initialNodes: Node[] = [
  {
    id: 'node_A',
    type: 'input', // React Flow的默认输入节点
    position: { x: 100, y: 50 },
    data: { label: 'Input Node' },
  },
  {
    id: 'node_B',
    type: 'default', // 代表我们的LLMNode
    position: { x: 100, y: 200 },
    data: { label: 'LLM Node' },
  },
  {
    id: 'node_C',
    type: 'output', // React Flow的默认输出节点
    position: { x: 100, y: 350 },
    data: { label: 'Output Node' },
  },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: 'node_A', target: 'node_B' },
];

// 我们后端API的地址
const API_URL = 'http://localhost:8000/api/graphs/execute';

function App() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [result, setResult] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );
  const onConnect: OnConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    []
  );

  const handleRunGraph = async () => {
    setIsLoading(true);
    setResult('Executing graph...');

    // 将React Flow的格式转换为我们后端定义的格式
    const graphPayload = {
      nodes: [
        { id: 'node_A', type: 'InputNode', data: { value: 'Tell me a short story about a robot.' } },
        { id: 'node_B', type: 'LLMNode', data: { prompt: '{{node_A.output}}' } },
        { id: 'node_C', type: 'OutputNode', data: { template: 'Final result is: {{node_B.output}}' } },
      ],
      edges: edges.map(e => ({ source: e.source, target: e.target })),
    };

    try {
      const response = await axios.post(API_URL, graphPayload);
      // 我们只显示最后一个节点的输出作为最终结果
      setResult(JSON.stringify(response.data['node_C'], null, 2));
    } catch (error: any) {
      setResult(`Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ padding: '10px', background: '#333', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Hevno MVP</h1>
        <button onClick={handleRunGraph} disabled={isLoading}>
          {isLoading ? 'Running...' : 'Run Graph'}
        </button>
      </header>
      <div style={{ flex: 1, display: 'flex' }}>
        <div style={{ flex: '2' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
          >
            <Controls />
            <Background />
          </ReactFlow>
        </div>
        <div style={{ flex: '1', padding: '10px', background: '#2a2a2a', overflowY: 'auto' }}>
          <h2>Result</h2>
          <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word', color: 'lightgreen' }}>
            {result}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default App;