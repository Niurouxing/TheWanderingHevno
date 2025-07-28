import { Router, Request, Response } from 'express';
import { runGraph } from '../services/pipelineService';
import { GraphSchema } from '@hevno/core/models';
import { simpleStoryGraph } from '../testGraph'; // Import the test graph

const router = Router();

// Add a new route for testing purposes
router.post('/run-test', async (req: Request, res: Response) => {
    try {
        console.log('Running test graph...');
        // Define a simple input for our test graph
        const inputs = {
            'input-1': 'A story about a brave knight and a clever dragon who become friends.',
        };

        const result = await runGraph(simpleStoryGraph, inputs);
        res.json({ success: true, result });

    } catch (error) {
        console.error('Error running test graph:', error);
        if (error instanceof Error) {
            res.status(500).json({ success: false, message: 'Failed to run test graph', error: error.message });
        } else {
            res.status(500).json({ success: false, message: 'An unknown error occurred.' });
        }
    }
});


router.post('/run', async (req: Request, res: Response) => {
  try {
    const { graph, inputs } = req.body;

    // Validate the graph structure using our shared Zod schema
    const parsedGraph = GraphSchema.parse(graph);

    const result = await runGraph(parsedGraph, inputs);
    res.json({ success: true, result });
  } catch (error) {
    console.error('Error running graph:', error);
    // Return a more informative error, potentially with Zod validation details
    if (error instanceof Error) {
        res.status(400).json({ success: false, message: 'Failed to run graph', error: error.message });
    } else {
        res.status(400).json({ success: false, message: 'An unknown error occurred.' });
    }
  }
});

export default router;
