import Fastify from 'fastify';
import { pipelineRoutes } from './api/v1/endpoints/pipeline';

const server = Fastify({
  logger: {
    transport: {
      target: 'pino-pretty',
    },
  },
});

// Register routes
server.register(pipelineRoutes, { prefix: '/api/v1/pipeline' });

const start = async () => {
  try {
    await server.listen({ port: 3000 });
    server.log.info(`Server listening on http://localhost:3000`);
  } catch (err) {
    server.log.error(err);
    process.exit(1);
  }
};

start();
