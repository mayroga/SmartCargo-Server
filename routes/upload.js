import express from "express";
import multer from "multer";
import { uploadFiles } from "../services/uploadService.js";

export const uploadRoute = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

uploadRoute.post("/", upload.array("photos", 10), async (req, res) => {
  try {
    const urls = await uploadFiles(req.files);
    res.json({ urls });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
