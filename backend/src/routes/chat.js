import { Router } from 'express';
import multer from 'multer';
import * as chatController from '../controllers/chatController.js';

const router = Router();

const upload = multer({
  storage: multer.memoryStorage(),
});

router.post('/chat', upload.single('file'), chatController.chat);

export default router;
