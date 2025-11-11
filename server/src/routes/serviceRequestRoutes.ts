// src/routes/serviceRequestRoute.ts
import { Router } from "express";
import { createServiceRequest } from "../controllers/serviceRequestController";

const router = Router();

router.post("/", createServiceRequest);

export default router;
