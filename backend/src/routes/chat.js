import express from 'express';
import * as chatController from '../controllers/chatController.js';

const router = express.Router();

router.post('/chat', chatController.chat);

export default router;
