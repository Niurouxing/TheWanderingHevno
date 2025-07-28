import { Graph, GraphNode, ProcessorNode } from '@hevno/core/models';
import { GoogleGenerativeAI } from '@google/generative-ai';

// Load the API key from environment variables
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
if (!GEMINI_API_KEY) {
    throw new Error("GEMINI_API_KEY is not set in the environment variables.");
}
const genAI = new GoogleGenerativeAI(GEMINI_API_KEY);

/**
 * Executes a graph based on its definition.
 *
 * @param graph The graph definition.
 * @param inputs The initial inputs for the graph's input nodes.
 * @returns The final outputs from the graph's output nodes.
 */
export async function runGraph(graph: Graph, inputs: Record<string, any>): Promise<any> {
  console.log('Executing graph:', graph.id);

  const executionOrder = topologicalSort(graph);
  console.log('Execution order:', executionOrder.map(n => n.id));

  const nodeOutputs: Record<string, Record<string, any>> = {};

  // Initialize with the graph's main inputs
  for (const node of graph.nodes) {
    if (node.type === 'input' && inputs[node.id]) {
        // An input node has one output port, let's assume the first one.
        const outputPortId = node.outputs[0]?.id || 'output';
        nodeOutputs[node.id] = { [outputPortId]: inputs[node.id] };
    }
  }

  for (const node of executionOrder) {
    console.log(`[Executing Node] ID: ${node.id}, Type: ${node.type}`);

    // Gather inputs for the current node from its predecessors
    const currentNodeInputs: Record<string, any> = {};
    const relevantEdges = graph.edges.filter(edge => edge.targetNodeId === node.id);
    for (const edge of relevantEdges) {
        const sourceOutput = nodeOutputs[edge.sourceNodeId];
        if (sourceOutput && sourceOutput[edge.sourceOutputId] !== undefined) {
            currentNodeInputs[edge.targetInputId] = sourceOutput[edge.sourceOutputId];
        }
    }

    let outputs: Record<string, any> = {};

    // Execute node based on its type
    switch (node.type) {
        case 'processor':
            outputs = await executeProcessorNode(node, currentNodeInputs);
            break;
        // TODO: Implement other node types like 'map', 'router'
        case 'input':
            // Input nodes are pre-filled, no execution needed, just pass through
            outputs = nodeOutputs[node.id] || {};
            break;
        case 'output':
             // Output nodes just collect input
             outputs = currentNodeInputs;
             break;
    }
    
    nodeOutputs[node.id] = outputs;
  }

  // Collect results from the output nodes
  const finalResult: Record<string, any> = {};
  for (const node of graph.nodes) {
    if (node.type === 'output') {
      finalResult[node.id] = nodeOutputs[node.id];
    }
  }

  console.log('Graph execution finished.');
  return {
    message: "Graph execution complete.",
    finalResult,
  };
}

async function executeProcessorNode(node: ProcessorNode, inputs: Record<string, any>): Promise<Record<string, any>> {
    const { runtime } = node;
    switch (runtime.type) {
        case 'llm':
            if (runtime.provider === 'gemini') {
                const model = genAI.getGenerativeModel({ model: runtime.model });
                // Assuming the prompt comes from an input port named 'prompt'
                const prompt = inputs['prompt'] || '';
                console.log(`  [LLM Call] Prompt: "${prompt}"`);
                const result = await model.generateContent(prompt);
                const response = await result.response;
                const text = response.text();
                console.log(`  [LLM Response] Text: "${text.substring(0, 100)}..."`);
                // The output is sent to the first declared output port
                const outputPortId = node.outputs[0]?.id || 'output';
                return { [outputPortId]: text };
            } else {
                throw new Error(`Unsupported LLM provider: ${runtime.provider}`);
            }
        case 'function':
            // TODO: Implement function execution logic
            console.log(`  [Function Call] ${runtime.functionName} with inputs:`, inputs);
            return { output: `Result of ${runtime.functionName}` }; // Placeholder
        default:
            return {};
    }
}


/**
 * Performs a topological sort on the nodes of a graph.
 * This determines the correct order of execution based on dependencies.
 * @param graph The graph to sort.
 * @returns An array of nodes in execution order.
 * @throws An error if the graph has a cycle.
 */
function topologicalSort(graph: Graph): GraphNode[] {
    const inDegree = new Map<string, number>();
    const adj = new Map<string, string[]>();
    const idToNode = new Map(graph.nodes.map(n => [n.id, n]));

    // Initialize in-degree and adjacency list
    for (const node of graph.nodes) {
        inDegree.set(node.id, 0);
        adj.set(node.id, []);
    }

    // Build graph representation from edges
    for (const edge of graph.edges) {
        adj.get(edge.sourceNodeId)?.push(edge.targetNodeId);
        inDegree.set(edge.targetNodeId, (inDegree.get(edge.targetNodeId) || 0) + 1);
    }

    // Find all nodes with an in-degree of 0
    const queue: string[] = [];
    for (const [nodeId, degree] of inDegree.entries()) {
        if (degree === 0) {
            queue.push(nodeId);
        }
    }

    const sortedOrder: GraphNode[] = [];
    while (queue.length > 0) {
        const nodeId = queue.shift()!;
        const node = idToNode.get(nodeId);
        if (node) {
            sortedOrder.push(node);
        }

        for (const neighborId of adj.get(nodeId) || []) {
            const newDegree = (inDegree.get(neighborId) || 1) - 1;
            inDegree.set(neighborId, newDegree);
            if (newDegree === 0) {
                queue.push(neighborId);
            }
        }
    }

    if (sortedOrder.length !== graph.nodes.length) {
        throw new Error("Graph has a cycle, topological sort failed.");
    }

    return sortedOrder;
}
