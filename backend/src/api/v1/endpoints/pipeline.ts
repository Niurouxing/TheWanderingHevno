import { FastifyInstance } from 'fastify';
import { GraphSchema } from '../../models/graph_schema';
import { PipelineRunner } from '../../services/pipeline_runner';

export async function pipelineRoutes(fastify: FastifyInstance) {
  fastify.post('/run', {
    schema: {
      body: GraphSchema,
    },
  }, async (request, reply) => {
    try {
      const graph = request.body;
      const runner = new PipelineRunner(graph);
      const result = await runner.run();
      return reply.send(result);
    } catch (error) {
      fastify.log.error(error);
      // Check if error is an instance of Error to safely access message property
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      return reply.status(500).send({ error: 'Pipeline execution failed', details: errorMessage });
    }
  });
}
