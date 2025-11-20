import express from "express";
import { requirePayment } from "../payment.middleware.js";
import { analyzeCargo } from "../services/analyzeService.js";

export const analyzeRoute = express.Router();

analyzeRoute.post("/", requirePayment("analysis"), async (req, res) => {
  try {
    const result = await analyzeCargo(req.body);
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
