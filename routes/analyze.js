import express from "express";
import { analyzeService } from "../services/analyzeService.js";
import { requirePayment } from "../payment.middleware.js";

const router = express.Router();

router.post("/", requirePayment("analysis"), async (req, res) => {
  const result = await analyzeService(req.body);
  res.json(result);
});

export default router;
