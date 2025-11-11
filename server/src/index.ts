import express, { Application, Request, Response } from "express";
import mongoose from "mongoose";
import cors from "cors";
import dotenv from "dotenv";
import { createServer } from "http";
import { Server } from "socket.io";

import authRoutes from "./routes/auth";
import announcementRoutes from "./routes/announcementsRoutes";
import branchRoutes from "./routes/branchRoutes";
import userRoutes from "./routes/userRoutes";
import promoRoutes from "./routes/promoRoutes";
import unavailabilityRoutes from "./routes/unavailabilityRoutes";
import customerRoutes from "./routes/customerRoutes";
import lineItemRoutes from "./routes/lineItemRoutes";
import appointmentsRoutes from "./routes/appointmentsRoutes";
import serviceRoutes from "./routes/serviceRoutes";
import serviceRequestRoutes from "./routes/serviceRequestRoutes";
import transactionRoutes from "./routes/transactionRoutes";
import paymentsRoutes from "./routes/paymentsRoutes";
import analyticsRoutes from "./routes/analyticsRoutes";
import { initSocket } from "./socket";
import lineItemImageRoutes from "./routes/lineItemImageRoutes";
import datesRoutes from "./routes/datesRoutes";
import batchRoutes from "./routes/batchRoutes";

dotenv.config();

const app: Application = express();
const httpServer = createServer(app);

// Setup socket.io
const io = new Server(httpServer, {
  cors: {
    origin: "*", // adjust to your frontend domain later
  },
});

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use("/api/announcements", announcementRoutes);
app.use("/api/branches", branchRoutes);
app.use("/api", userRoutes);
app.use("/api/promos", promoRoutes);
app.use("/api/unavailability", unavailabilityRoutes);
app.use("/api/customers", customerRoutes);
app.use("/api/line-items", lineItemRoutes);
app.use("/api/appointments", appointmentsRoutes);
app.use("/api/services", serviceRoutes);
app.use("/api/service-request", serviceRequestRoutes);
app.use("/transactions", transactionRoutes);
app.use("/api/line-item-image", lineItemImageRoutes);
app.use("/api/transactions", transactionRoutes);
app.use("/api/dates", datesRoutes);
app.use("/api/payments", paymentsRoutes);
app.use("/api/batch", batchRoutes);
app.use("/api/analytics", analyticsRoutes);

// Test route
app.get("/", (req: Request, res: Response) => {
  res.send("API is running...");
});

// Auth routes
app.use("/api/auth", authRoutes);

// Connect DB + Init Socket
const MONGO_URI = process.env.MONGO_URI || "";
mongoose
  .connect(MONGO_URI)
  .then(() => {
    console.log("✅ MongoDB connected");
    initSocket(io, mongoose.connection); // 👈 pass DB + socket
  })
  .catch((err) => console.error("❌ MongoDB connection error:", err));

// Start server
const PORT = process.env.PORT || 5000;
httpServer.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
