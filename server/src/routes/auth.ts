// src/routes/auth.ts
import { Router } from "express";
import { login } from "../controllers/auth";

const router = Router();

// POST /api/auth/login
router.post("/login", login);

export default router;
