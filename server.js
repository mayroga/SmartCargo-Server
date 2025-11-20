import express from "express";
import bodyParser from "body-parser";
import { requirePayment } from "./payment.middleware.js";

const app = express();
app.use(bodyParser.json());

app.post("/upload", async (req, res) => {
  // Lógica para subir fotos
  res.json({ success: true, message: "Fotos subidas correctamente." });
});

app.post("/analyze-basic", requirePayment("basic"), async (req, res) => {
  // Análisis simple
  res.json({ level: "basic", result: "Análisis básico completado." });
});

app.post("/analyze-premium", requirePayment("premium"), async (req, res) => {
  // Análisis completo con OCR y PDF
  res.json({ level: "premium", result: "Análisis premium completado." });
});

app.post("/analyze-enterprise", requirePayment("enterprise"), async (req, res) => {
  // Todo + asesoría avanzada
  res.json({ level: "enterprise", result: "Análisis enterprise completado." });
});

app.post("/ocr", async (req, res) => {
  // Lógica OCR con Google Vision
  res.json({ success: true, message: "OCR completado." });
});

app.post("/generate-pdf", async (req, res) => {
  // Generación PDF profesional
  res.json({ success: true, message: "PDF generado." });
});

app.post("/auth/login", async (req, res) => {
  // Autenticación de usuarios
  res.json({ success: true, token: "dummy-token" });
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => {
  console.log(`Servidor SmartCargo corriendo en puerto ${PORT}`);
});
