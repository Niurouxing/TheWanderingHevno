
import express from 'express';
import cors from 'cors';
import pipelineRouter from './routes/pipeline';

const app = express();
const port = 3000;

// Middlewares
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/pipeline', pipelineRouter);

app.get('/', (req, res) => {
  res.send('Hevno Backend is running!');
});

app.listen(port, () => {
  console.log(`Server is listening on http://localhost:${port}`);
});
