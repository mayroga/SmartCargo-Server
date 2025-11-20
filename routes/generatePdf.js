import express from "express";
import { authService } from "../services/authService.js";

const router = express.Router();

router.post("/login", async (req, res) => {
  const token = await authService.login(req.body);
  res.json({ token });
});

export default router;
