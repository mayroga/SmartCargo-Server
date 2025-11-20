import express from "express";
import { requirePayment } from "../payment.middleware.js";
import { generatePdfReport } from "../services/pdfService.js";

export const pdfRoute = express.Router();

pdfRoute.post("/", requirePayment("pdf"), async (req, res) => {
  try {
    const pdfBuffer = await generatePdfReport(req.body);
    res.setHeader("Content-Type", "application/pdf");
    res.send(pdfBuffer);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
