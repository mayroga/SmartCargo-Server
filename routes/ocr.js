import express from "express";
import { ocrService } from "../services/ocrService.js";
import { requirePayment } from "../payment.middleware.js";

const router = express.Router();

router.post("/", requirePayment("ocr"), async (req, res) => {
  const result = await ocrService(req.body);
  res.json(result);
});

export default router;
