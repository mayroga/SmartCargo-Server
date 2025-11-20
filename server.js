import express from "express";
import mongoose from "mongoose";
import dotenv from "dotenv";
import cors from "cors";
import { uploadRoute } from "./routes/upload.js";
import { analyzeRoute } from "./routes/analyze.js";
import { ocrRoute } from "./routes/ocr.js";
import { pdfRoute } from "./routes/generatePdf.js";
import { authRoute } from "./routes/auth.js";

dotenv.config();
const app = express();
app.use(cors());
app.use(express.json({ limit: "50mb" }));

// Rutas
app.use("/upload", uploadRoute);
app.use("/analyze", analyzeRoute);
app.use("/ocr", ocrRoute);
app.use("/generate-pdf", pdfRoute);
app.use("/auth", authRoute);

// MongoDB
mongoose.connect(process.env.MONGO_URI)
  .then(() => console.log("✅ MongoDB connected"))
  .catch(err => console.error("❌ MongoDB error:", err));

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => console.log(`🚀 Backend running on port ${PORT}`));
