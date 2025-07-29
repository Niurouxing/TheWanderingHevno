// packages/api-server/src/index.ts
import 'dotenv/config';
import Fastify from 'fastify';
import cors from '@fastify/cors';
import { Server } from 'socket.io';
import { GraphExecutor } from '@hevno/core-engine'; // 导入执行器
import { Graph } from '@hevno/schemas'; // 导入图类型

const fastify = Fastify({ logger: true });

// 注册 CORS
fastify.register(cors, {
  origin: '*', // 开发时允许所有来源
});

// HTTP 路由
fastify.get('/', async (request, reply) => {
  return { message: 'Welcome to Hevno API' };
});

// 启动服务器
const start = async () => {
  try {
    await fastify.listen({ port: 3001 });

    const io = new Server(fastify.server, { cors: { origin: '*' } });
    const graphExecutor = new GraphExecutor(); // 实例化执行器

    io.on('connection', (socket) => {
      fastify.log.info(`Client connected: ${socket.id}`);

      // 监听 'execute_graph' 事件
      socket.on('execute_graph', async (data: { graph: Graph, inputs: Record<string, any> }) => {
        fastify.log.info(`Received execute_graph request from ${socket.id}`);
        try {
          // 这里可以添加 Zod 验证 data.graph 和 data.inputs
          const resultContext = await graphExecutor.execute(data.graph, data.inputs);
          
          // 将最终输出节点的输出发送回客户端
          const outputNodes = data.graph.nodes.filter(n => n.type === 'output');
          const finalOutputs: Record<string, any> = {};
          for (const node of outputNodes) {
              finalOutputs[node.id] = resultContext.outputs[node.id];
          }

          socket.emit('execution_result', { success: true, outputs: finalOutputs });
        } catch (error: any) {
          fastify.log.error(error);
          socket.emit('execution_result', { success: false, error: error.message });
        }
      });

      socket.on('disconnect', () => {
        fastify.log.info(`Client disconnected: ${socket.id}`);
      });
      
      socket.emit('welcome', 'Connected to Hevno WebSocket!');
    });

  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();