import express from "express";
import { requirePayment } from "../payment.middleware.js";
import { analyzeOCR } from "../services/ocrService.js";

export const ocrRoute = express.Router();

ocrRoute.post("/", requirePayment("ocr"), async (req, res) => {
  try {
    const result = await analyzeOCR(req.body.photos);
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
