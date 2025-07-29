import { GraphSchema, GraphNode, Edge } from '@hevno/schemas';

// 使用 Kahn 算法进行拓扑排序
export function topologicalSort(nodes: GraphNode[], edges: Edge[]): string[] {
  const inDegree = new Map<string, number>();
  const adjList = new Map<string, string[]>();
  const sortedOrder: string[] = [];
  const queue: string[] = [];

  // 初始化入度和邻接表
  for (const node of nodes) {
    inDegree.set(node.id, 0);
    adjList.set(node.id, []);
  }

  // 计算每个节点的入度
  for (const edge of edges) {
    adjList.get(edge.sourceNodeId)?.push(edge.targetNodeId);
    inDegree.set(edge.targetNodeId, (inDegree.get(edge.targetNodeId) ?? 0) + 1);
  }

  // 将所有入度为 0 的节点加入队列
  for (const [nodeId, degree] of inDegree.entries()) {
    if (degree === 0) {
      queue.push(nodeId);
    }
  }

  // 处理队列中的节点
  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    sortedOrder.push(nodeId);

    for (const neighborId of adjList.get(nodeId) ?? []) {
      const newDegree = (inDegree.get(neighborId) ?? 1) - 1;
      inDegree.set(neighborId, newDegree);
      if (newDegree === 0) {
        queue.push(neighborId);
      }
    }
  }

  // 检查是否有环 (如果排序后的节点数不等于总节点数)
  if (sortedOrder.length !== nodes.length) {
    throw new Error('Graph has at least one cycle. Topological sort is not possible.');
  }

  return sortedOrder;
}