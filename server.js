import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import mongoose from "mongoose";

import uploadRouter from "./routes/upload.js";
import analyzeRouter from "./routes/analyze.js";
import ocrRouter from "./routes/ocr.js";
import pdfRouter from "./routes/generatePdf.js";
import authRouter from "./routes/auth.js";

dotenv.config();
const app = express();

app.use(cors());
app.use(express.json());

app.use("/upload", uploadRouter);
app.use("/analyze", analyzeRouter);
app.use("/ocr", ocrRouter);
app.use("/generate-pdf", pdfRouter);
app.use("/auth", authRouter);

const PORT = process.env.PORT || 5000;

mongoose.connect(process.env.MONGO_URI, {
  useNewUrlParser: true,
  useUnifiedTopology: true
}).then(() => {
  console.log("MongoDB connected");
  app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
}).catch(err => console.error(err));
