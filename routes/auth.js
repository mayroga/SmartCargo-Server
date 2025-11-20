import express from "express";
import { loginUser } from "../services/authService.js";

export const authRoute = express.Router();

authRoute.post("/login", async (req, res) => {
  try {
    const token = await loginUser(req.body.email, req.body.password);
    res.json({ token });
  } catch (err) {
    res.status(401).json({ error: err.message });
  }
});
