
import { Graph } from '@hevno/core/models';

export const simpleStoryGraph: Graph = {
  id: 'graph-1',
  name: 'Simple Story Generation Graph',
  nodes: [
    {
      id: 'input-1',
      name: 'Story Topic',
      type: 'input',
      position: { x: 100, y: 100 },
      inputs: [],
      outputs: [{ id: 'output', name: 'Topic', type: 'string' }],
    },
    {
      id: 'processor-1',
      name: 'Story Generator',
      type: 'processor',
      position: { x: 400, y: 100 },
      runtime: {
        type: 'llm',
        provider: 'gemini',
        model: 'gemini-1.5-flash', // Corrected model name
        temperature: 0.8,
      },
      inputs: [{ id: 'prompt', name: 'Prompt', type: 'string' }],
      outputs: [{ id: 'output', name: 'Story', type: 'string' }],
    },
    {
      id: 'output-1',
      name: 'Final Story',
      type: 'output',
      position: { x: 700, y: 100 },
      inputs: [{ id: 'input', name: 'Story', type: 'string' }],
      outputs: [],
    },
  ],
  edges: [
    {
      id: 'edge-1',
      sourceNodeId: 'input-1',
      sourceOutputId: 'output',
      targetNodeId: 'processor-1',
      targetInputId: 'prompt',
    },
    {
      id: 'edge-2',
      sourceNodeId: 'processor-1',
      sourceOutputId: 'output',
      targetNodeId: 'output-1',
      targetInputId: 'input',
    },
  ],
};
