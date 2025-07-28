import { Graph, GraphNode } from "../../models/graph_schema";

export class PipelineRunner {
    private graph: Graph;

    constructor(graph: Graph) {
        this.graph = graph;
    }

    public async run(): Promise<any> {
        console.log("Running pipeline with graph:", this.graph.name);

        // Naive execution: find the input node and start from there.
        // This is a placeholder for a proper topological sort based execution.
        const inputNode = this.graph.nodes.find(n => n.type === 'input');
        if (!inputNode) {
            throw new Error("Pipeline must have an 'input' node.");
        }

        const executionContext: Record<string, any> = {};

        // For now, just simulate a run and return the structure.
        // In the next step, we will implement the actual execution logic.
        await this.executeNode(inputNode, executionContext);

        console.log("Pipeline execution finished.");
        return {
            message: `Pipeline '${this.graph.name}' executed successfully.`,
            finalContext: executionContext
        };
    }

    private async executeNode(node: GraphNode, context: Record<string, any>) {
        console.log(`Executing node: ${node.name} (Type: ${node.type})`);
        // Placeholder for node execution logic
        context[node.id] = {
            output: `Output from ${node.name}`
        };
    }
}
