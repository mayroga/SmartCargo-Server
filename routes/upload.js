import express from "express";
import { uploadService } from "../services/uploadService.js";
import { requirePayment } from "../payment.middleware.js";

const router = express.Router();

router.post("/", requirePayment("upload"), async (req, res) => {
  const result = await uploadService(req.body);
  res.json(result);
});

export default router;
