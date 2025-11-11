// src/routes/serviceRoutes.ts
import express from "express";
import { getAllServices, addService, getServiceById } from "../controllers/serviceController";

const router = express.Router();

// GET all services
router.get("/", getAllServices);

// POST a new service
router.post("/", addService);

// GET service by id
router.get("/:serviceId", getServiceById);

export default router;
